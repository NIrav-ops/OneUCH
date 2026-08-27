from django.utils import timezone
import requests
from django.utils.dateparse import parse_datetime
from inbox.models import Conversation, InboxMessage
from inbox.utils.conversation_key import generate_conversation_key
from oauth_tokens.models import OAuthToken
from inbox.services.sync_status import update_sync_status
from django.conf import settings
from microsoftapis.utils import get_microsoft_access_token
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from inbox.services.conversation_cache import invalidate_conversation_cache

from knowledge.services.message_processor import (MessageProcessor,)

def fetch_outlook_emails(*, user, email_account, limit=20):

    update_sync_status(
        user=user,
        platform="outlook",
        status="syncing",
        progress=0,
    )

    try:
        access_token = get_microsoft_access_token(user)
    except Exception as exc:
        update_sync_status(
            user=user,
            platform="outlook",
            status="failed",
            progress=0,
            error_message=str(exc),
        )
        raise

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.get(
        "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages",
        headers=headers,
        params={
            "$top": limit,
            "$select": "id,subject,bodyPreview,conversationId,isRead,from,receivedDateTime,hasAttachments",
            "$expand": "attachments"
        }
    )
    print("OUTLOOK API STATUS:", response.status_code)
    print("OUTLOOK API RESPONSE:", response.text[:500])
    
    if response.status_code != 200:
        update_sync_status(
            user=user,
            platform="outlook",
            status="failed",
            progress=0,
            error_message=response.text,
        )
        raise RuntimeError(
            "Microsoft Graph Outlook sync failed "
            f"with status {response.status_code}"
        )

    messages = response.json().get("value", [])
    organization = user.organization_membership.organization

    print("OUTLOOK MESSAGES COUNT:", len(messages))

    message_obj = None

    for msg in messages:

        platform = "outlook"

        external_id = msg.get("id")
        thread_id = msg.get("conversationId")

        subject = msg.get("subject") or "No Subject"

        sender = (
            msg.get("from", {})
            .get("emailAddress", {})
            .get("address", "")
        ) or ""

        body = msg.get("bodyPreview", "")

        # =========================
        # 📎 EXTRACT ATTACHMENTS (FINAL)
        # =========================

        attachments = []

        if msg.get("hasAttachments"):
            for att in msg.get("attachments", []):
                if att.get("@odata.type") == "#microsoft.graph.fileAttachment":
                    attachments.append({
                        "filename": att.get("name"),
                        "attachment_id": att.get("id"),
                        "mime_type": att.get("contentType"),
                    })

        print("📎 OUTLOOK ATTACHMENTS:", attachments)

        received_at = parse_datetime(msg.get("receivedDateTime"))

        is_read = msg.get("isRead", False)
        is_starred = False

        # =========================
        # CONVERSATION ACCOUNT REPAIR
        # =========================
        conversation_key = f"outlook_{thread_id}"

        conversation = Conversation.objects.filter(
            user=user,
            conversation_key=conversation_key,
        ).first()

        if (
            conversation
            and conversation.email_account_id is None
        ):
            conversation.email_account = email_account
            conversation.save(
                update_fields=[
                    "email_account",
                ]
            )

        # Skip messages already synced for this account.
        if InboxMessage.objects.filter(
            external_message_id=external_id,
            email_account=email_account,
        ).exists():
            continue

        if not conversation:
            conversation = Conversation.objects.create(
                user=user,
                organization=organization,
                conversation_key=conversation_key,
                subject=subject,
                email_account=email_account,
            )

        # =========================
        # SAVE MESSAGE
        # =========================
        message_obj = InboxMessage.objects.create(
            user=user,
            organization=organization,
            conversation=conversation,
            platform=platform,
            external_message_id=external_id,
            external_conversation_id=thread_id,
            sender=sender,
            recipients="",
            subject=subject,
            attachment_meta=attachments,
            body=body,
            received_at=received_at,
            is_read=is_read,
            is_starred=is_starred,
            direction="inbound",
            is_draft=False,
            email_account=email_account,
        )

        # ==========================================================
        # Enterprise Knowledge Processing
        # ==========================================================

        try:

            processor = MessageProcessor()

            processor.process_message(
                organization=organization,
                message=message_obj,
                sender=sender,
                subject=subject,
                body=body,
                source_channel="outlook",
            )

            print(
                f"🧠 Outlook Knowledge processed: {subject}"
            )

        except Exception as exc:

            print(
                f"❌ Outlook Knowledge Processing Failed: {exc}"
            )

        # =========================
        # UPDATE CONVERSATION
        # =========================
        conversation.last_message = message_obj
        conversation.last_message_at = message_obj.received_at
        conversation.last_message_preview = (
            message_obj.body[:120] if message_obj.body else "No preview"
        )

        conversation.subject = message_obj.subject or conversation.subject

        conversation.save(update_fields=[
            "last_message",
            "last_message_at",
            "last_message_preview",
            "subject"
        ])

        invalidate_conversation_cache(user.id)

# Sync completion must run even when there are
# zero new messages or every fetched message is a duplicate.
    update_sync_status(
        user=user,
        platform="outlook",
        status="success",
        progress=100,
    )


# Send realtime websocket event

    if message_obj: 

        channel_layer = get_channel_layer()

        async_to_sync(channel_layer.group_send)(
            f"inbox_{user.id}",
                {
                    "type": "inbox_update",
                    "data": {
                        "event": "new_email",
                        "conversation_id": conversation.id,
                        "subject": conversation.subject,
                        "sender": sender,
                        "preview": conversation.last_message_preview,
                        "received_at": conversation.last_message_at.isoformat(),
                        "platform": conversation.email_account.account_type,
                    }   
                }
            )

    print("Outlook sync completed.")