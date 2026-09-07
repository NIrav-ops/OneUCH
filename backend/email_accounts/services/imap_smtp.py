import imaplib
import email
from email.header import decode_header
from django.utils import timezone

from email_accounts.services.mailbox_network_policy import (
    connect_validated_mailbox_endpoint,
    create_verified_tls_context,
    validate_mailbox_endpoint,
)

from inbox.models import Conversation, InboxMessage
from inbox.services.sync_status import update_sync_status
from inbox.notifications.services import create_notification
from inbox.utils.conversation_key import generate_conversation_key
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


class _PinnedIMAP4SSL(
    imaplib.IMAP4_SSL
):
    """
    IMAP TLS client whose TCP connection is pinned to the
    already-policy-validated address set while TLS hostname
    verification continues to use the configured hostname.
    """

    def __init__(
        self,
        endpoint,
        *,
        timeout=None,
    ):
        self._validated_endpoint = (
            endpoint
        )

        super().__init__(
            endpoint.host,
            endpoint.port,
            ssl_context=(
                create_verified_tls_context()
            ),
            timeout=timeout,
        )

    def _create_socket(
        self,
        timeout,
    ):
        raw_socket = (
            connect_validated_mailbox_endpoint(
                endpoint=(
                    self._validated_endpoint
                ),
                timeout=timeout,
            )
        )

        try:
            return (
                self.ssl_context
                .wrap_socket(
                    raw_socket,
                    server_hostname=(
                        self.host
                    ),
                )
            )

        except Exception:
            raw_socket.close()
            raise



# ================================
# IMAP FETCH (Folder + Incremental + Priority)
# ================================

def fetch_imap_emails(
    *,
    user,
    email_account,
    password,
    limit=10
):
    """
    Folder-aware incremental IMAP sync with smart priority scoring.
    """

    if email_account is None:
        raise ValueError(
            "IMAP EmailAccount does not exist"
        )

    if (
        email_account.user_id
        !=
        user.id
    ):
        raise ValueError(
            "IMAP mailbox ownership mismatch."
        )

    provider_platform = email_account.account_type

    organization = (
        email_account.organization
    )

    if (
        organization.id
        !=
        user.organization_membership.organization_id
    ):
        raise ValueError(
            "IMAP mailbox workspace mismatch."
        )

    update_sync_status(
        user=user,
        platform=provider_platform,
        status="syncing",
        progress=0,
    )

    if email_account.account_type != "imap":
        return

    try:
        imap_endpoint = (
            validate_mailbox_endpoint(
                host=(
                    email_account
                    .imap_server
                ),
                port=(
                    email_account
                    .imap_port
                ),
                protocol="imap",
            )
        )

        mail = _PinnedIMAP4SSL(
            imap_endpoint
        )

        mail.login(email_account.email_address, password)

        if not isinstance(email_account.last_synced_uids, dict):
            email_account.last_synced_uids = {}

        status, folder_list = mail.list()
        if status != "OK":
            raise Exception("Unable to fetch folder list")

        gmail_folders = {}
        for folder in folder_list:
            decoded = folder.decode()
            if "Sent" in decoded:
                gmail_folders["sent"] = decoded.split(' "/" ')[-1].strip('"')
            elif "Draft" in decoded:
                gmail_folders["draft"] = decoded.split(' "/" ')[-1].strip('"')
            elif "Trash" in decoded:
                gmail_folders["trash"] = decoded.split(' "/" ')[-1].strip('"')

        gmail_folders["inbox"] = "INBOX"

        total_processed = 0

        for folder_key, folder_name in gmail_folders.items():

            status, _ = mail.select(f'"{folder_name}"')
            if status != "OK":
                continue

            folder_last_uid = email_account.last_synced_uids.get(folder_key, 0)

            try:
                last_uid = int(folder_last_uid)
            except (TypeError, ValueError):
                last_uid = 0

            status, messages = mail.uid(
                "search",
                None,
                f"(UID {last_uid + 1}:*)"
            )

            if status != "OK":
                continue

            email_uids = messages[0].split()
            if not email_uids:
                continue

            email_uids = email_uids[-limit:]

            for uid in email_uids:

                status, msg_data = mail.uid("fetch", uid, "(RFC822 FLAGS)")
                if status != "OK":
                    continue

                flags = msg_data[0][0].decode()
                is_starred = "\\Flagged" in flags

                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                message_id = msg.get("Message-ID")
                in_reply_to = msg.get("In-Reply-To")
                references = msg.get("References")

                if in_reply_to:
                    conversation_id = in_reply_to.strip()
                elif references:
                    conversation_id = references.split()[-1].strip()
                elif message_id:
                    conversation_id = message_id.strip()
                else:
                    conversation_id = uid.decode()

                subject, encoding = decode_header(msg.get("Subject", ""))[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or "utf-8", errors="ignore")

                sender = msg.get("From", "")
                body = ""

                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            payload = part.get_payload(decode=True)
                            if payload:
                                body = payload.decode(errors="ignore")
                            break
                else:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        body = payload.decode(errors="ignore")

                # -------- Priority Engine --------
                HIGH = ["urgent", "asap", "immediately", "critical", "action required"]
                MEDIUM = ["invoice", "payment", "due", "deadline", "important"]

                combined = f"{subject} {body}".lower()
                priority_score = 0

                for word in HIGH:
                    if word in combined:
                        priority_score += 40

                for word in MEDIUM:
                    if word in combined:
                        priority_score += 20

                if subject and subject.isupper():
                    priority_score += 10

                priority_score = min(priority_score, 100)
                is_priority = priority_score >= 50

                external_id = f"{folder_key}_{uid.decode()}"

                existing_message = InboxMessage.objects.filter(
                    external_message_id=external_id,
                    email_account=email_account
                ).first()

                if not existing_message:

                    conversation_key = generate_conversation_key(
                        "imap",
                        None,
                        subject,
                        sender
                    )

                    conversation, _ = Conversation.objects.get_or_create(
                        user=user,
                        organization=organization,
                        subject=subject or "No Subject",
                    )

                    if InboxMessage.objects.filter(
                        external_message_id=external_id,
                        email_account=email_account
                    ).exists():
                        continue
                try:
                    message_obj = InboxMessage.objects.create(
                        user=user,
                        organization=organization,
                        conversation=conversation,
                        platform=provider_platform,
                        external_message_id=external_id,
                        external_conversation_id=conversation_id,
                        folder=folder_key,
                        direction="inbound" if folder_key == "inbox" else "outbound",
                        in_reply_to=in_reply_to,
                        sender=sender,
                        recipients=email_account.email_address,
                        subject=subject or "",
                        body=body,
                        is_starred=is_starred,
                        received_at=timezone.now(),
                        is_read=False if folder_key == "inbox" else True,
                        is_priority=is_priority,
                        priority_score=priority_score,
                        email_account=email_account,
                    )
                except Exception as exc:
                    raise RuntimeError(
                        "IMAP message persistence failed."
                    ) from exc

                # ✅ Conversation materialization
                conversation.last_message = message_obj
                conversation.last_message_at = message_obj.received_at
                conversation.last_message_preview = message_obj.body[:120] if message_obj.body else ""

                conversation.subject = message_obj.subject or conversation.subject

                conversation.save(update_fields=[
                    "last_message",
                    "last_message_at",
                    "last_message_preview",
                    "subject"
                    ])

                conversation.save(update_fields=["search_index"])

                if not message_obj.is_read:
                    conversation.unread_count += 1

                conversation.save()

                total_processed += 1

            # Save latest UID
            email_account.last_synced_uids[folder_key] = int(email_uids[-1])
            email_account.save()

        update_sync_status(
            user=user,
            platform=provider_platform,
            status="success",
            progress=100,
        )

        mail.logout()

    except Exception as e:

        update_sync_status(
            user=user,
            platform=provider_platform,
            status="failed",
            error_message=(
                "IMAP synchronization failed."
            ),
        )

        channel_layer = get_channel_layer()

        async_to_sync(channel_layer.group_send)(
            f"inbox_{user.id}",
            {
                "type": "inbox_update",
                "data": {
                    "event":
                        "sync_failed"
                }
            }
        )

        raise
            

# ================================
# SMTP SEND
# ================================

import smtplib
import socket

from email.message import EmailMessage


class _PinnedSMTPSSL(
    smtplib.SMTP_SSL
):
    """
    SMTP TLS client whose TCP connection is pinned to the
    validated address set while certificate hostname
    verification uses the configured SMTP hostname.
    """

    def __init__(
        self,
        endpoint,
        *,
        timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
        source_address=None,
    ):
        self._validated_endpoint = (
            endpoint
        )

        super().__init__(
            endpoint.host,
            endpoint.port,
            timeout=timeout,
            source_address=source_address,
            context=(
                create_verified_tls_context()
            ),
        )

    def _get_socket(
        self,
        host,
        port,
        timeout,
    ):
        raw_socket = (
            connect_validated_mailbox_endpoint(
                endpoint=(
                    self._validated_endpoint
                ),
                timeout=timeout,
                source_address=(
                    self.source_address
                ),
            )
        )

        try:
            return (
                self.context
                .wrap_socket(
                    raw_socket,
                    server_hostname=(
                        self._host
                    ),
                )
            )

        except Exception:
            raw_socket.close()
            raise


def send_via_smtp(
    *,
    email_account,
    to_email,
    subject,
    body,
    inbox_message=None,
    password=None
):

    try:
        if not password:
            raise ValueError("SMTP password not configured")

        smtp_endpoint = (
            validate_mailbox_endpoint(
                host=(
                    email_account
                    .smtp_server
                ),
                port=(
                    email_account
                    .smtp_port
                ),
                protocol="smtp",
            )
        )

        msg = EmailMessage()
        msg["From"] = email_account.email_address
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(body)

        server = _PinnedSMTPSSL(
            smtp_endpoint
        )

        server.login(email_account.email_address, password)
        server.send_message(msg)
        server.quit()

        if inbox_message:
            inbox_message.status = "sent"
            inbox_message.last_attempt_at = timezone.now()
            inbox_message.save()

            create_notification(
                user=inbox_message.user,
                title="Email sent",
                message=f"Your email '{inbox_message.subject}' was sent successfully.",
                notification_type="success",
            )

    except Exception as e:

        if inbox_message:
            inbox_message.status = "failed"
            inbox_message.error_reason = str(e)
            inbox_message.retry_count += 1
            inbox_message.last_attempt_at = timezone.now()
            inbox_message.save()

            create_notification(
                user=inbox_message.user,
                title="Email failed",
                message=f"Failed to send email '{inbox_message.subject}'.",
                notification_type="error",
            )

        raise
