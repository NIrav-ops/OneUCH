from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64
import requests

from inbox.models import Conversation, InboxMessage
from googleapis.utils import get_gmail_credentials
from microsoftapis.utils import get_microsoft_access_token
from inbox.utils.conversation_key import generate_conversation_key


class UnifiedSendMessageAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        try:
            user = request.user

            to = request.data.get("to")
            subject = request.data.get("subject", "")
            body = request.data.get("body", "")
            conversation_id = request.data.get("conversation_id")

            if not to:
                return Response({"error": "Recipient required"}, status=400)

            # =========================
            # ACCOUNT
            # =========================
            account_id = request.data.get("account_id")

            if account_id:
                account = user.email_accounts.filter(id=account_id).first()
            else:
                account = user.email_accounts.first()

            if not account:
                return Response({"error": "No email account connected"}, status=400)

            account_type = account.account_type

            # =========================
            # CONVERSATION
            # =========================
            conversation = None
            if conversation_id:
                conversation = Conversation.objects.filter(
                    id=conversation_id,
                    user=user
                ).first()

                if not conversation:
                    return Response({"error": "Conversation not found"}, status=404)

            if conversation is None:
                conversation_key = generate_conversation_key(
                    account_type,
                    None,
                    subject,
                    to
                )

                conversation, _ = Conversation.objects.get_or_create(
                    user=user,
                    conversation_key=conversation_key,
                    defaults={
                        "organization": user.organization_membership.organization,
                        "subject": subject or "New Message",
                        "email_account": account,
                        "last_message_preview": "",
                    }
                )

            # =========================
            # SEND EMAIL
            # =========================
            if account_type == "gmail":

                creds = get_gmail_credentials(user)
                service = build("gmail", "v1", credentials=creds)

                message = MIMEText(body)
                message["to"] = to
                message["subject"] = subject

                raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

                service.users().messages().send(
                    userId="me",
                    body={"raw": raw}
                ).execute()

            elif account_type == "outlook":

                token = get_microsoft_access_token(user)

                requests.post(
                    "https://graph.microsoft.com/v1.0/me/sendMail",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "message": {
                            "subject": subject,
                            "body": {
                                "contentType": "Text",
                                "content": body,
                            },
                            "toRecipients": [
                                {"emailAddress": {"address": to}}
                            ],
                        }
                    },
                )

            # =========================
            # SAVE MESSAGE (ONE TIME ONLY ✅)
            # =========================
            message_obj = InboxMessage.objects.create(
                user=user,
                organization=user.organization_membership.organization,
                platform=account_type,
                external_message_id="sent",
                sender=account.email_address,
                recipients=to,
                subject=subject or "No Subject",
                body=body,
                is_read=True,
                email_account=account,
                direction="outbound",
                is_draft=False,
                received_at=timezone.now(),
                conversation=conversation   # 🔥 THIS IS THE FIX
            )

            # UPDATE CONVERSATION
            conversation.last_message = message_obj
            conversation.last_message_at = message_obj.received_at
            conversation.last_message_preview = body[:120] if body else ""

            conversation.save()

            # =========================
            # REALTIME UPDATE
            # =========================
            channel_layer = get_channel_layer()

            async_to_sync(channel_layer.group_send)(
                f"inbox_{user.id}",
                {
                    "type": "send_update",
                    "data": {"message": "new_email"}
                }
            )

            return Response({
                "status": "sent",
                "conversation_id": conversation.id,
                "message_id": message_obj.id,
            })

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)
