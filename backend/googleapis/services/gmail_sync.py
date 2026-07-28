from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timezone as dt_timezone

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from inbox.models import Conversation, InboxMessage
from inbox.utils.conversation_key import generate_conversation_key
from oauth_tokens.models import OAuthToken
from inbox.services.conversation_cache import invalidate_conversation_cache
from django.conf import settings
from knowledge.services.message_processor import MessageProcessor

def extract_attachments(payload):
    attachments = []

    def parse_parts(parts):
        for part in parts:
            filename = part.get("filename")
            body = part.get("body", {})
            mime_type = part.get("mimeType")

            # ✅ REAL attachment
            if filename and body.get("attachmentId"):
                attachments.append({
                    "filename": filename,
                    "attachment_id": body.get("attachmentId"),
                    "mime_type": mime_type,
                })

            # ✅ INLINE attachment (IMPORTANT EDGE CASE)
            elif filename and body.get("data"):
                attachments.append({
                    "filename": filename,
                    "attachment_id": None,
                    "mime_type": mime_type,
                })

            # 🔁 RECURSIVE (VERY IMPORTANT)
            if part.get("parts"):
                parse_parts(part["parts"])

    if payload.get("parts"):
        parse_parts(payload["parts"])

    return attachments


def fetch_gmail_emails(*, user, email_account, limit=20):

    token = OAuthToken.objects.filter(
        user=user,
        provider="google",
        is_active=True
    ).first()

    if not token:
        print("❌ No active Google OAuth token found.")
        return

    creds = Credentials(
        token=token.access_token,
        refresh_token=token.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/gmail.modify"],
    )

    service = build("gmail", "v1", credentials=creds)

    # 🔥 USE THREADS API (NOT MESSAGES)
    results = service.users().threads().list(
        userId="me",
        q=f"to:{email_account.email_address} OR from:{email_account.email_address}",
        maxResults=limit
    ).execute()

    threads = results.get("threads", [])

    organization = user.organization_membership.organization

    for thread in threads:

        try:
            thread_id = thread["id"]

            thread_data = service.users().threads().get(
                userId="me",
                id=thread_id
            ).execute()

            messages = thread_data.get("messages", [])

            for msg in messages:

                external_id = msg["id"]

                # Skip duplicates
                existing_message = InboxMessage.objects.filter(
                    external_message_id=external_id,
                    email_account=email_account,
                ).first()

                if existing_message:

                    print(
                        f"⏭️ Skipping existing Gmail message: {existing_message.id}"
                    )

                    continue

                # =========================
                # EXTRACT DATA
                # =========================

                platform = "gmail"
                payload = msg.get("payload", {})
                headers = payload.get("headers", [])

                # 🔥 ENTERPRISE ATTACHMENT EXTRACTION (NESTED SAFE)
                attachments = []

                def extract_parts(parts):
                    for part in parts:
                        filename = part.get("filename")
                        body = part.get("body", {})

                        if filename and body.get("attachmentId"):
                            attachments.append({
                                "filename": filename,
                                "attachment_id": body.get("attachmentId"),
                                "mime_type": part.get("mimeType"),
                            })

                        # 🔁 recursive (VERY IMPORTANT)
                        if part.get("parts"):
                            extract_parts(part.get("parts"))

                # run extraction
                if payload.get("parts"):
                    extract_parts(payload.get("parts"))  

                subject = None
                sender = ""
                recipients = ""

                for h in headers:
                    name = h.get("name", "").lower()
                    value = h.get("value", "")

                    if name == "subject":
                        subject = value

                    elif name == "from":
                        sender = value

                    elif name == "to":
                        recipients = value


                # =========================
                # 🚨 LABELS + DIRECTION (FIRST DEFINE THIS)
                # =========================

                label_ids = msg.get("labelIds", [])
                user_email = email_account.email_address.lower()
                # 🎯 FINAL DIRECTION LOGIC (NO DUPLICATES)

                if "INBOX" in label_ids:
                    direction = "inbound"

                elif "SENT" in label_ids:
                    direction = "outbound"

                else:
                    continue

                # =========================
                # FALLBACK SUBJECT
                # =========================

                if not subject:
                    subject = msg.get("snippet")

                if not subject:
                    subject = "No Subject"

                # =========================
                # BODY
                # =========================

                body = msg.get("snippet", "")

                # =========================
                # THREAD + MESSAGE ID
                # =========================

                thread_id = msg.get("threadId")
                external_id = msg.get("id")

                # =========================
                # TIME
                # =========================

                internal_date = int(msg.get("internalDate", 0)) / 1000
                received_at = datetime.fromtimestamp(internal_date, tz=dt_timezone.utc)

                # =========================
                # FLAGS
                # =========================

                is_read = "UNREAD" not in label_ids
                is_starred = "STARRED" in label_ids

                print("📎 ATTACHMENTS FOUND:", attachments)

                # =========================
                # CONVERSATION FIX
                # =========================

                conversation_key = f"gmail_{thread_id}"

                conversation = Conversation.objects.filter(
                    user=user,
                    conversation_key=conversation_key
                ).first()

                if not conversation:
                    conversation = Conversation.objects.create(
                        user=user,
                        organization=organization,
                        conversation_key=conversation_key,
                        subject=subject or "No Subject",
                        email_account=email_account,
                    )

                if not conversation.external_conversation_id:
                    conversation.external_conversation_id = thread_id
                    conversation.save(update_fields=["external_conversation_id"])

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
                    recipients=recipients,
                    subject=subject,
                    attachment_meta=attachments,
                    body=body,
                    received_at=received_at,
                    is_read=is_read,
                    is_starred=is_starred,
                    direction=direction,
                    is_draft=False,
                    email_account=email_account,
                )

                # =========================
                # 🔄 Update Conversation
                # =========================
                # AFTER creating message_obj

                conversation.last_message = message_obj
                conversation.last_message_at = message_obj.received_at
                conversation.last_message_preview = (
                    message_obj.body[:120] if message_obj.body else "No preview"
                )
                conversation.subject = message_obj.subject or conversation.subject
                
                if message_obj.subject:
                    conversation.subject = message_obj.subject

                conversation.save(update_fields=[
                    "last_message",
                    "last_message_at",
                    "last_message_preview",
                    "subject"
                    ])

                invalidate_conversation_cache(user.id)

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
                        source_channel="gmail",
                    )

                    print(
                        f"🧠 Knowledge processed: {subject}"
                    )

                except Exception as exc:

                    print(
                        f"❌ Knowledge Processing Failed: {exc}"
                    )  

                # =========================
                # 📡 WebSocket Event
                # =========================
                channel_layer = get_channel_layer()

                async_to_sync(channel_layer.group_send)(
                    f"inbox_{user.id}",
                    {
                        "type": "inbox_update",
                        "data": {
                            "event": "new_email",
                            "conversation_id": conversation.id,
                            "subject": subject,
                            "sender": sender,
                            "preview": message_obj.body[:120],
                            "received_at": received_at.isoformat(),
                            "platform": "gmail",
                        }
                    }
                )
                
                print(
                        f"✅ Gmail synced: {subject}"
                    )
                print(
                        f"Conversation ID : {conversation.id}"
                    )

                print(
                        f"Message ID : {message_obj.id}"
                    )

        except Exception as e:
            print("❌ Gmail Sync Failed:", str(e))
            continue