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


def _structured_delivery_addresses(
    inbox_message,
    fallback_to,
):
    recipient_meta = (
        inbox_message.recipient_meta
        if isinstance(
            inbox_message.recipient_meta,
            dict,
        )
        else {}
    )


    to_addresses = [
        str(
            item.get(
                "email",
                "",
            )
        )
        .strip()
        .lower()

        for item
        in (
            recipient_meta.get(
                "to",
                [],
            )
            or []
        )

        if (
            isinstance(
                item,
                dict,
            )
            and
            item.get(
                "email"
            )
        )
    ]


    cc_addresses = [
        str(
            item.get(
                "email",
                "",
            )
        )
        .strip()
        .lower()

        for item
        in (
            recipient_meta.get(
                "cc",
                [],
            )
            or []
        )

        if (
            isinstance(
                item,
                dict,
            )
            and
            item.get(
                "email"
            )
        )
    ]


    to_value = (
        ", ".join(
            to_addresses
        )
        if to_addresses
        else fallback_to
    )


    return (
        to_value,
        cc_addresses,
    )


def _deliver_reply_message(
    *,
    email_account,
    inbox_message,
    fallback_to,
    subject,
    body,
    reply_mode="reply",
):
    (
        to_value,
        cc_addresses,
    ) = (
        _structured_delivery_addresses(
            inbox_message,
            fallback_to,
        )
    )


    if email_account.account_type == "gmail":

        return (
            send_gmail_reply(
                user=(
                    email_account.user
                ),
                to_email=(
                    to_value
                ),
                subject=subject,
                body=body,
                cc_emails=(
                    cc_addresses
                ),
                thread_id=(
                    inbox_message
                    .external_conversation_id
                ),
                reply_to_message_id=(
                    inbox_message
                    .in_reply_to
                ),
            )
        )


    if email_account.account_type == "outlook":

        return (
            send_outlook_reply(
                user=(
                    email_account.user
                ),
                to_email=(
                    to_value
                ),
                subject=subject,
                body=body,
                cc_emails=(
                    cc_addresses
                ),
                reply_to_message_id=(
                    inbox_message
                    .in_reply_to
                ),
                reply_mode=(
                    reply_mode
                ),
            )
        )


    if email_account.account_type == "imap":

        smtp_to = (
            to_value
        )


        if cc_addresses:

            smtp_to = (
                smtp_to
                + ", "
                + ", ".join(
                    cc_addresses
                )
            )


        return (
            send_via_smtp(
                email_account=(
                    email_account
                ),
                to_email=smtp_to,
                subject=subject,
                body=body,
                inbox_message=(
                    inbox_message
                ),
                password=(
                    email_account
                    .smtp_password
                ),
            )
        )


    raise ValueError(
        "Unsupported email account type: "
        f"{email_account.account_type}"
    )


def _mark_delivery_success(
    *,
    inbox_message,
    provider_result,
):
    provider_id = None


    if isinstance(
        provider_result,
        dict,
    ):

        provider_id = (
            provider_result.get(
                "id"
            )
        )


    inbox_message.status = (
        "sent"
    )

    inbox_message.folder = (
        "sent"
    )

    inbox_message.error_reason = (
        ""
    )

    inbox_message.last_attempt_at = (
        timezone.now()
    )

    inbox_message.external_message_id = (
        provider_id
        or
        "sent"
    )


    inbox_message.save(
        update_fields=[
            "status",
            "folder",
            "error_reason",
            "last_attempt_at",
            "external_message_id",
        ]
    )


@shared_task(
    bind=True,
    max_retries=3,
)
def send_email_task(
    self,
    email_account_id,
    to_email,
    subject,
    body,
    inbox_message_id,
    reply_mode="reply",
):
    inbox_message = None


    try:

        email_account = (
            EmailAccount.objects
            .get(
                id=email_account_id
            )
        )


        inbox_message = (
            InboxMessage.objects
            .get(
                id=inbox_message_id
            )
        )


        if (
            inbox_message.user_id
            !=
            email_account.user_id
        ):

            raise ValueError(
                "Reply mailbox ownership mismatch."
            )


        provider_result = (
            _deliver_reply_message(
                email_account=(
                    email_account
                ),
                inbox_message=(
                    inbox_message
                ),
                fallback_to=(
                    to_email
                ),
                subject=subject,
                body=body,
                reply_mode=(
                    reply_mode
                ),
            )
        )


        _mark_delivery_success(
            inbox_message=(
                inbox_message
            ),
            provider_result=(
                provider_result
            ),
        )


    except Exception as exc:

        if inbox_message is None:
            raise


        inbox_message.retry_count += 1

        inbox_message.error_reason = (
            str(
                exc
            )
        )

        inbox_message.last_attempt_at = (
            timezone.now()
        )


        if (
            inbox_message.retry_count
            >=
            MAX_RETRIES
        ):

            inbox_message.status = (
                "failed"
            )


            inbox_message.save(
                update_fields=[
                    "retry_count",
                    "error_reason",
                    "last_attempt_at",
                    "status",
                ]
            )


            return


        inbox_message.status = (
            "queued"
        )


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
    failed_messages = (
        InboxMessage.objects
        .filter(
            status="failed",
            retry_count__lt=(
                MAX_RETRIES
            ),
        )
    )


    for message in failed_messages:

        message.status = (
            "retrying"
        )

        message.last_attempt_at = (
            timezone.now()
        )

        message.save(
            update_fields=[
                "status",
                "last_attempt_at",
            ]
        )


        try:

            email_account = (
                message.email_account
            )


            if email_account is None:

                email_account = (
                    message.user
                    .email_accounts
                    .filter(
                        is_active=True
                    )
                    .first()
                )


            if email_account is None:

                raise ValueError(
                    "No email account available for retry."
                )


            recipient_meta = (
                message.recipient_meta
                if isinstance(
                    message.recipient_meta,
                    dict,
                )
                else {}
            )


            reply_mode = (
                "reply_all"
                if recipient_meta.get(
                    "cc"
                )
                else "reply"
            )


            provider_result = (
                _deliver_reply_message(
                    email_account=(
                        email_account
                    ),
                    inbox_message=(
                        message
                    ),
                    fallback_to=(
                        message.recipients
                    ),
                    subject=(
                        message.subject
                    ),
                    body=(
                        message.body
                    ),
                    reply_mode=(
                        reply_mode
                    ),
                )
            )


            _mark_delivery_success(
                inbox_message=(
                    message
                ),
                provider_result=(
                    provider_result
                ),
            )


            create_notification(
                user=message.user,
                type="send_retried",
                title=(
                    "Message sent after retry"
                ),
                message=(
                    message.subject
                ),
            )


        except Exception as exc:

            message.status = (
                "failed"
            )

            message.error_reason = (
                str(
                    exc
                )
            )

            message.last_attempt_at = (
                timezone.now()
            )

            message.save(
                update_fields=[
                    "status",
                    "error_reason",
                    "last_attempt_at",
                ]
            )


            create_notification(
                user=message.user,
                type="send_failed",
                title=(
                    "Message delivery failed"
                ),
                message=(
                    message.subject
                ),
            )
