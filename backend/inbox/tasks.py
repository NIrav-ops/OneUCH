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

from inbox.services.persistent_outbound_attachments import (
    load_persisted_outbound_attachments,
)

from inbox.services.outbound_idempotency import (
    OutboundIdempotencyUnavailable,
    acquire_outbound_delivery_lock,
    complete_outbound_intent,
    get_outbound_intent_for_message,
    mark_outbound_intent_uncertain,
    release_outbound_delivery_lock,
)

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


    attachments = (
        load_persisted_outbound_attachments(
            message=inbox_message
        )
    )


    if email_account.account_type == "gmail":

        gmail_kwargs = {
            "user":
                email_account.user,

            "to_email":
                to_value,

            "subject":
                subject,

            "body":
                body,

            "cc_emails":
                cc_addresses,

            "thread_id":
                (
                    inbox_message
                    .external_conversation_id
                ),

            "reply_to_message_id":
                (
                    inbox_message
                    .in_reply_to
                ),
        }


        # Preserve the legacy call signature when there are no
        # files. Existing provider behavior and tests therefore
        # remain backward compatible.
        if attachments:

            gmail_kwargs[
                "attachments"
            ] = attachments


        return (
            send_gmail_reply(
                **gmail_kwargs
            )
        )


    if email_account.account_type == "outlook":

        outlook_kwargs = {
            "user":
                email_account.user,

            "to_email":
                to_value,

            "subject":
                subject,

            "body":
                body,

            "cc_emails":
                cc_addresses,

            "reply_to_message_id":
                (
                    inbox_message
                    .in_reply_to
                ),

            "reply_mode":
                reply_mode,
        }


        if attachments:

            outlook_kwargs[
                "attachments"
            ] = attachments


        return (
            send_outlook_reply(
                **outlook_kwargs
            )
        )


    if email_account.account_type == "imap":

        if attachments:

            raise ValueError(
                "Reply attachments are currently supported "
                "only for Gmail and Microsoft 365."
            )


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

    intent = None

    delivery_lock_acquired = False

    provider_attempt_started = False


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


        # A completed local delivery is authoritative. A Celery
        # replay of the same task must never call the provider
        # again.
        if (
            inbox_message.status
            ==
            "sent"
        ):

            return {
                "status":
                    "already_sent",

                "message_id":
                    inbox_message.id,

                "provider_message_id":
                    inbox_message.external_message_id,
            }


        try:

            intent = (
                get_outbound_intent_for_message(
                    user_id=(
                        inbox_message.user_id
                    ),
                    message_id=(
                        inbox_message.id
                    ),
                )
            )

        except OutboundIdempotencyUnavailable:

            # Legacy replies created without an Idempotency-Key
            # remain compatible with the prior task behavior.
            intent = None


        # If the provider was already accepted and the Redis
        # intent reached completed state, recover local state
        # without ever calling the provider a second time.
        if (
            intent
            and
            intent.get(
                "state"
            )
            ==
            "completed"
        ):

            provider_id = (
                intent.get(
                    "provider_message_id"
                )
            )


            _mark_delivery_success(
                inbox_message=(
                    inbox_message
                ),
                provider_result=(
                    {
                        "id":
                            provider_id
                    }
                    if provider_id
                    else
                    {}
                ),
            )


            return {
                "status":
                    "already_provider_accepted",

                "message_id":
                    inbox_message.id,

                "provider_message_id":
                    provider_id,
            }


        if (
            intent
            and
            intent.get(
                "state"
            )
            ==
            "delivery_uncertain"
        ):

            return {
                "status":
                    "delivery_uncertain",

                "message_id":
                    inbox_message.id,

                "error": (
                    "Provider delivery outcome is uncertain. "
                    "Automatic resend is blocked."
                ),
            }


        if intent:

            delivery_lock_acquired = (
                acquire_outbound_delivery_lock(
                    user_id=(
                        inbox_message.user_id
                    ),
                    idempotency_key=(
                        intent[
                            "idempotency_key"
                        ]
                    ),
                )
            )


            if not delivery_lock_acquired:

                return {
                    "status":
                        "duplicate_delivery_in_progress",

                    "message_id":
                        inbox_message.id,
                }


        provider_attempt_started = True


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


        # Provider acceptance is recorded in the semantic intent
        # before local state finalization. If the DB save below
        # fails and Celery retries, the retry repairs the local
        # row from this completed intent rather than resending.
        if intent:

            try:

                intent = (
                    complete_outbound_intent(
                        user_id=(
                            inbox_message.user_id
                        ),
                        idempotency_key=(
                            intent[
                                "idempotency_key"
                            ]
                        ),
                        message_id=(
                            inbox_message.id
                        ),
                        provider_message_id=(
                            provider_result.get(
                                "id"
                            )
                            if isinstance(
                                provider_result,
                                dict,
                            )
                            else None
                        ),
                    )
                )

            except OutboundIdempotencyUnavailable as exc:

                # The provider call returned successfully, which is
                # sufficient evidence that delivery was accepted.
                # Never schedule another provider call merely because
                # the safety record could not be finalized.
                _mark_delivery_success(
                    inbox_message=(
                        inbox_message
                    ),
                    provider_result=(
                        provider_result
                    ),
                )


                return {
                    "status":
                        "sent_idempotency_finalize_degraded",

                    "message_id":
                        inbox_message.id,

                    "provider_message_id":
                        inbox_message.external_message_id,

                    "warning": (
                        "Provider accepted the message, but "
                        "idempotency state finalization was unavailable. "
                        "Automatic resend was suppressed."
                    ),

                    "idempotency_error":
                        str(
                            exc
                        ),
                }


        _mark_delivery_success(
            inbox_message=(
                inbox_message
            ),
            provider_result=(
                provider_result
            ),
        )


        return {
            "status":
                "sent",

            "message_id":
                inbox_message.id,

            "provider_message_id":
                inbox_message.external_message_id,
        }


    except Exception as exc:

        if inbox_message is None:
            raise


        # Once provider delivery has been attempted under a
        # semantic idempotency intent, a transport exception can
        # mean either "not delivered" OR "provider accepted but the
        # response was lost". Automatically retrying that ambiguous
        # state can create a duplicate real email.
        #
        # Fail closed instead. A repeated API request with the same
        # key receives delivery_uncertain and cannot resend.
        if (
            intent
            and
            provider_attempt_started
            and
            intent.get(
                "state"
            )
            !=
            "completed"
        ):

            try:

                intent = (
                    mark_outbound_intent_uncertain(
                        user_id=(
                            inbox_message.user_id
                        ),
                        idempotency_key=(
                            intent[
                                "idempotency_key"
                            ]
                        ),
                        message_id=(
                            inbox_message.id
                        ),
                        error=exc,
                    )
                )

            except OutboundIdempotencyUnavailable:

                # Even if Redis is unavailable now, suppressing the
                # Celery retry is safer than risking a second provider
                # send after an ambiguous first attempt.
                pass


            inbox_message.retry_count += 1

            inbox_message.error_reason = (
                "Delivery outcome uncertain; automatic resend "
                "suppressed: "
                +
                str(
                    exc
                )
            )

            inbox_message.last_attempt_at = (
                timezone.now()
            )

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


            return {
                "status":
                    "delivery_uncertain",

                "message_id":
                    inbox_message.id,

                "error":
                    inbox_message.error_reason,
            }


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


    finally:

        if (
            delivery_lock_acquired
            and
            intent
        ):

            release_outbound_delivery_lock(
                user_id=(
                    inbox_message.user_id
                ),
                idempotency_key=(
                    intent[
                        "idempotency_key"
                    ]
                ),
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
