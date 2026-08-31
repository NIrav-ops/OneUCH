# ============================================
# IMPORTS
# ============================================

from celery import shared_task
from django.utils import timezone
from django.contrib.auth import get_user_model

from email_accounts.models import EmailAccount
from oauth_tokens.models import OAuthToken

from inbox.models import InboxMessage
from inbox.models import Conversation
from inbox.utils.sync_lock import acquire_sync_lock, release_sync_lock

from notifications.services import create_notification

from email_accounts.services.gmail_api import send_gmail_reply
from email_accounts.services.microsoft_api import send_outlook_reply
from email_accounts.services.imap_smtp import send_via_smtp, fetch_imap_emails

from googleapis.services.gmail_sync import fetch_gmail_emails
from microsoftapis.services.outlook_sync import fetch_outlook_emails

from approvals.tasks import analyze_new_approvals
from platform_core.observability.logger import get_logger, log_event

logger = get_logger("oneuch.runtime.scheduler")

User = get_user_model()
MAX_RETRIES = 3


# ============================================
# TASK 1: SYNC ALL EMAIL ACCOUNTS
# ============================================

@shared_task
def sync_email_account(
    email_account_id,
):
    """
    Governed single-mailbox synchronization task.

    This is the common runtime path for:
    - manual Sync mailbox
    - scheduled mailbox synchronization

    Provider ingestion remains authoritative inside:
    - fetch_gmail_emails
    - fetch_outlook_emails
    - fetch_imap_emails

    The existing account-level distributed sync lock prevents
    overlapping manual/scheduled execution for the same mailbox.
    """

    account = (
        EmailAccount.objects
        .select_related(
            "user"
        )
        .filter(
            id=email_account_id,
            is_active=True,
        )
        .first()
    )


    if account is None:

        log_event(
            logger,
            "warning",
            "sync.account.skipped_missing",
            account_id=(
                email_account_id
            ),
        )

        return {
            "status":
                "skipped",

            "reason":
                "inactive_or_missing",
        }


    lock = (
        acquire_sync_lock(
            account.id
        )
    )


    if not lock:

        log_event(
            logger,
            "info",
            "sync.account.skipped_lock",
            account_id=(
                account.id
            ),
            provider=(
                account.account_type
            ),
        )

        return {
            "status":
                "skipped",

            "reason":
                "already_syncing",

            "provider":
                account.account_type,
        }


    log_event(
        logger,
        "debug",
        "sync.account.selected",
        account_id=(
            account.id
        ),
        provider=(
            account.account_type
        ),
    )


    try:

        # ----------------------------------------------------
        # GMAIL
        # ----------------------------------------------------

        if (
            account.account_type
            ==
            "gmail"
        ):

            log_event(
                logger,
                "info",
                "sync.account.started",
                account_id=(
                    account.id
                ),
                provider="gmail",
            )


            fetch_gmail_emails(
                user=account.user,
                email_account=(
                    account
                ),
            )


        # ----------------------------------------------------
        # MICROSOFT
        # ----------------------------------------------------

        elif (
            account.account_type
            ==
            "outlook"
        ):

            log_event(
                logger,
                "info",
                "sync.account.started",
                account_id=(
                    account.id
                ),
                provider="outlook",
            )


            fetch_outlook_emails(
                user=account.user,
                email_account=(
                    account
                ),
            )


        # ----------------------------------------------------
        # IMAP / SMTP
        # ----------------------------------------------------

        elif (
            account.account_type
            ==
            "imap"
        ):

            log_event(
                logger,
                "info",
                "sync.account.started",
                account_id=(
                    account.id
                ),
                provider="imap",
            )


            # Generic IMAP currently uses the existing temporary
            # SMTP/app-password field for provider authentication.
            imap_password = (
                account.smtp_password
            )


            if not imap_password:

                log_event(
                    logger,
                    "warning",
                    (
                        "sync.account."
                        "skipped_missing_credential"
                    ),
                    account_id=(
                        account.id
                    ),
                    provider="imap",
                )


                return {
                    "status":
                        "skipped",

                    "reason":
                        "missing_credential",

                    "provider":
                        "imap",
                }


            fetch_imap_emails(
                user=account.user,
                email_account=(
                    account
                ),
                password=(
                    imap_password
                ),
            )


        else:

            raise ValueError(
                "Unsupported email account type."
            )


        analyze_new_approvals.delay()


        log_event(
            logger,
            "info",
            "sync.account.completed",
            account_id=(
                account.id
            ),
            provider=(
                account.account_type
            ),
        )


        return {
            "status":
                "completed",

            "provider":
                account.account_type,
        }


    except Exception as exc:

        log_event(
            logger,
            "error",
            "sync.account.failed",
            account_id=(
                account.id
            ),
            provider=(
                account.account_type
            ),
            error_type=(
                type(exc).__name__
            ),
        )


        # A per-mailbox Celery task should be operationally
        # visible as failed. Provider services already persist
        # their own sync-health truth where supported.
        raise


    finally:

        release_sync_lock(
            lock
        )


@shared_task
def periodic_sync_all_users():
    """
    Scheduler fan-out.

    Celery Beat only identifies active mailboxes and queues the
    governed per-mailbox task. Provider network work executes in
    Celery workers rather than serially inside the scheduler job.
    """

    account_ids = list(
        EmailAccount.objects
        .filter(
            is_active=True
        )
        .values_list(
            "id",
            flat=True,
        )
    )


    queued_count = 0

    failed_count = 0


    for account_id in (
        account_ids
    ):

        try:

            sync_email_account.delay(
                account_id
            )

            queued_count += 1


        except Exception as exc:

            failed_count += 1


            log_event(
                logger,
                "error",
                "sync.account.queue_failed",
                account_id=(
                    account_id
                ),
                error_type=(
                    type(exc).__name__
                ),
            )


    log_event(
        logger,
        "info",
        "sync.scheduler.fanout",
        account_count=(
            len(account_ids)
        ),
        queued_count=(
            queued_count
        ),
        failed_count=(
            failed_count
        ),
    )


    if failed_count:

        raise RuntimeError(
            "Mailbox scheduler failed to queue "
            f"{failed_count} account(s)."
        )


    return {
        "queued":
            queued_count,

        "failed":
            failed_count,
    }


# ============================================
# TASK 2: SEND EMAIL (ASYNC)
# ============================================

@shared_task(bind=True, max_retries=3)
def send_email_task(
    self,
    email_account_id,
    to_email,
    subject,
    body,
    inbox_message_id,
):

    inbox_message = None

    try:

        email_account = EmailAccount.objects.get(
            id=email_account_id
        )

        inbox_message = InboxMessage.objects.get(
            id=inbox_message_id
        )

        # -----------------------------
        # Gmail
        # -----------------------------
        if email_account.account_type == "gmail":

            send_gmail_reply(
                user=email_account.user,
                to_email=to_email,
                subject=subject,
                body=body,
            )

        # -----------------------------
        # Outlook / Microsoft Graph
        # -----------------------------
        elif email_account.account_type == "outlook":

            send_outlook_reply(
                user=email_account.user,
                to_email=to_email,
                subject=subject,
                body=body,
            )

        # -----------------------------
        # IMAP / SMTP
        # -----------------------------
        elif email_account.account_type == "imap":

            send_via_smtp(
                email_account=email_account,
                to_email=to_email,
                subject=subject,
                body=body,
                inbox_message=inbox_message,
                password=email_account.smtp_password,
            )

        else:

            raise ValueError(
                "Unsupported email account type: "
                f"{email_account.account_type}"
            )

        inbox_message.status = "sent"
        inbox_message.error_reason = ""
        inbox_message.last_attempt_at = timezone.now()

        inbox_message.save(
            update_fields=[
                "status",
                "error_reason",
                "last_attempt_at",
            ]
        )

    except Exception as exc:

        if inbox_message is None:
            raise

        inbox_message.retry_count += 1
        inbox_message.error_reason = str(exc)
        inbox_message.last_attempt_at = timezone.now()

        if inbox_message.retry_count >= MAX_RETRIES:

            inbox_message.status = "failed"

            inbox_message.save(
                update_fields=[
                    "retry_count",
                    "error_reason",
                    "last_attempt_at",
                    "status",
                ]
            )

            return

        inbox_message.status = "queued"

        inbox_message.save(
            update_fields=[
                "retry_count",
                "error_reason",
                "last_attempt_at",
                "status",
            ]
        )

        raise self.retry(
            exc=exc,
            countdown=30,
        )


# ============================================
# TASK 3: RETRY FAILED MESSAGES
# ============================================

@shared_task
def retry_failed_messages():

    failed_messages = InboxMessage.objects.filter(
        status="failed",
        retry_count__lt=MAX_RETRIES
    )

    for msg in failed_messages:

        msg.status = "retrying"
        msg.last_attempt_at = timezone.now()
        msg.save()

        try:

            email_account = msg.email_account

            if not email_account:

                email_account = (
                    msg.user.email_accounts.filter(
                        is_active=True
                    ).first()
                )

            if not email_account:
                continue

            if email_account.account_type == "gmail":

                send_gmail_reply(
                    user=msg.user,
                    to_email=msg.recipients,
                    subject=msg.subject,
                    body=msg.body,
                )

            elif email_account.account_type == "outlook":

                send_outlook_reply(
                    user=msg.user,
                    to_email=msg.recipients,
                    subject=msg.subject,
                    body=msg.body,
                )

            elif email_account.account_type == "imap":

                send_via_smtp(
                    email_account=email_account,
                    to_email=msg.recipients,
                    subject=msg.subject,
                    body=msg.body,
                    inbox_message=msg,
                    password=email_account.smtp_password,
                )

            else:

                raise ValueError(
                    "Unsupported email account type: "
                    f"{email_account.account_type}"
                )

            create_notification(
                user=msg.user,
                type="send_retried",
                title="Message sent after retry",
                message=msg.subject
            )

        except Exception:

            create_notification(
                user=msg.user,
                type="send_failed",
                title="Message delivery failed",
                message=msg.subject
            )
