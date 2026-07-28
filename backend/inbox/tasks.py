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
from email_accounts.services.imap_smtp import send_via_smtp, fetch_imap_emails

from googleapis.services.gmail_sync import fetch_gmail_emails
from microsoftapis.services.outlook_sync import fetch_outlook_emails

from approvals.tasks import analyze_new_approvals

User = get_user_model()
MAX_RETRIES = 3


# ============================================
# TASK 1: SYNC ALL EMAIL ACCOUNTS
# ============================================

@shared_task
def periodic_sync_all_users():
    """
    Main scheduler task that syncs Gmail, Outlook and IMAP accounts.
    """

    accounts = EmailAccount.objects.filter(is_active=True)

    for account in accounts:

        lock = acquire_sync_lock(account.id)

        if not lock:
            print("SYNC SKIPPED - LOCK ACTIVE:", account.email_address)
            continue

        print("ACCOUNT TYPE:", account.account_type)

        try:

            # -----------------------------
            # GMAIL
            # -----------------------------
            if account.account_type == "gmail":

                print("SYNC START - GMAIL:", account.email_address)

                fetch_gmail_emails(
                    user=account.user,
                    email_account=account,
                )

            # -----------------------------
            # OUTLOOK
            # -----------------------------
            elif account.account_type == "outlook":

                print("SYNC START - OUTLOOK:", account.email_address)

                fetch_outlook_emails(
                    user=account.user,
                    email_account=account,
                )

            # -----------------------------
            # IMAP
            # -----------------------------
            elif account.account_type == "imap":

                print("SYNC START - IMAP:", account.email_address)

                if not account.imap_password:
                    continue

                fetch_imap_emails(
                    user=account.user,
                    email_account=account,
                    password=account.imap_password,
                )

            analyze_new_approvals.delay()

        except Exception as e:

            print("SYNC ERROR:", str(e))

        finally:

            release_sync_lock(account.id)

# ============================================
# TASK 2: SEND EMAIL (ASYNC)
# ============================================

@shared_task(bind=True, max_retries=3)
def send_email_task(self, email_account_id, to_email, subject, body, inbox_message_id):

    try:

        email_account = EmailAccount.objects.get(id=email_account_id)
        inbox_message = InboxMessage.objects.get(id=inbox_message_id)

        send_via_smtp(
            email_account=email_account,
            to_email=to_email,
            subject=subject,
            body=body,
            inbox_message=inbox_message,
            password=email_account.smtp_password,
        )

        inbox_message.status = "sent"
        inbox_message.last_attempt_at = timezone.now()
        inbox_message.save()

    except Exception as e:

        inbox_message.retry_count += 1
        inbox_message.error_reason = str(e)
        inbox_message.last_attempt_at = timezone.now()

        if inbox_message.retry_count >= MAX_RETRIES:
            inbox_message.status = "failed"
            inbox_message.save()
            return

        inbox_message.status = "queued"
        inbox_message.save()

        raise self.retry(exc=e, countdown=30)


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

            if msg.platform == "gmail":

                send_gmail_reply(
                    user=msg.user,
                    to_email=msg.recipients,
                    subject=msg.subject,
                    body=msg.body,
                    inbox_message=msg,
                )

            else:

                email_account = msg.user.email_accounts.filter(
                    is_active=True
                ).first()

                if not email_account:
                    continue

                send_via_smtp(
                    email_account=email_account,
                    to_email=msg.recipients,
                    subject=msg.subject,
                    body=msg.body,
                    inbox_message=msg,
                    password=email_account.smtp_password,
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