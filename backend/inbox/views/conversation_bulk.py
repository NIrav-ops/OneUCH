from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction

from inbox.models import Conversation
from googleapiclient.discovery import build

from googleapis.utils import get_gmail_credentials
from microsoftapis.utils import get_microsoft_access_token

import requests


class BulkMarkConversationReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        conversation_ids = request.data.get("conversation_ids", [])

        if not conversation_ids:
            return Response({"error": "No conversation_ids provided"}, status=400)

        conversations = Conversation.objects.filter(
            id__in=conversation_ids,
            user=request.user,
        ).select_related("email_account")

        results = []
        errors = []

        for conv in conversations:
            try:

                account = conv.email_account
                if not account:
                    raise Exception("No email account")

                account_type = account.account_type

                # =========================
                # 🔴 GMAIL
                # =========================
                if account_type == "gmail":

                    if not conv.external_conversation_id:
                        raise Exception("Missing Gmail threadId")

                    creds = get_gmail_credentials(request.user)
                    service = build("gmail", "v1", credentials=creds)

                    service.users().threads().modify(
                        userId="me",
                        id=conv.external_conversation_id,
                        body={"removeLabelIds": ["UNREAD"]}
                    ).execute()

                # =========================
                # 🔵 OUTLOOK
                # =========================
                elif account_type == "outlook":

                    token = get_microsoft_access_token(request.user)

                    for msg in conv.messages.all():
                        if not msg.external_message_id:
                            continue

                        requests.patch(
                            f"https://graph.microsoft.com/v1.0/me/messages/{msg.external_message_id}",
                            headers={
                                "Authorization": f"Bearer {token}",
                                "Content-Type": "application/json"
                            },
                            json={"isRead": True}
                        )

                # =========================
                # 🧠 UPDATE DB
                # =========================
                conv.unread_count = 0
                conv.save(update_fields=["unread_count"])

                conv.messages.update(is_read=True)

                results.append({
                    "conversation_id": conv.id,
                    "status": "read",
                })

            except Exception as e:
                print("❌ BULK READ ERROR:", str(e))

                errors.append({
                    "conversation_id": conv.id,
                    "error": str(e),
                })

        return Response({
            "updated": results,
            "errors": errors
        })


# ==========================================================
# ⭐ BULK STAR TOGGLE
# ==========================================================

class BulkToggleConversationStarAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        conversation_ids = request.data.get("conversation_ids", [])

        if not conversation_ids:
            return Response({"error": "No conversation_ids provided"}, status=400)

        conversations = Conversation.objects.filter(
            id__in=conversation_ids,
            user=request.user,
        ).select_related("email_account")

        results = []
        errors = []

        for conv in conversations:
            try:

                new_state = not conv.is_starred

                account = conv.email_account
                if not account:
                    raise Exception("No email account linked")

                account_type = account.account_type

                # =========================
                # 🔴 GMAIL
                # =========================
                if account_type == "gmail":

                    if not conv.external_conversation_id:
                        raise Exception("Missing Gmail threadId")

                    creds = get_gmail_credentials(request.user)
                    service = build("gmail", "v1", credentials=creds)

                    body = {}

                    if new_state:
                        body["addLabelIds"] = ["STARRED"]
                    else:
                        body["removeLabelIds"] = ["STARRED"]

                    service.users().threads().modify(
                        userId="me",
                        id=conv.external_conversation_id,
                        body=body
                    ).execute()

                # =========================
                # 🔵 OUTLOOK
                # =========================
                elif account_type == "outlook":

                    token = get_microsoft_access_token(request.user)

                    messages = conv.messages.all()

                    for msg in messages:
                        if not msg.external_message_id:
                            continue

                        requests.patch(
                            f"https://graph.microsoft.com/v1.0/me/messages/{msg.external_message_id}",
                            headers={
                                "Authorization": f"Bearer {token}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "flag": {
                                    "flagStatus": "flagged" if new_state else "notFlagged"
                                }
                            }
                        )

                # =========================
                # 🧠 UPDATE DB
                # =========================
                conv.is_starred = new_state
                conv.save(update_fields=["is_starred"])

                conv.messages.update(is_starred=new_state)

                results.append({
                    "conversation_id": conv.id,
                    "status": "read",
                })

            except Exception as e:
                print("❌ BULK STAR ERROR:", str(e))

                errors.append({
                    "conversation_id": conv.id,
                    "error": str(e),
                })

        return Response({
            "updated": results,
            "errors": errors
        })