from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from inbox.models import InboxMessage, Conversation


class ConversationDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):

        print("🔥 FINAL API HIT 🔥", conversation_id)

        user = request.user

        try:
            conversation = Conversation.objects.get(
                id=conversation_id,
                user=user
            )
        except Conversation.DoesNotExist:
            return Response({"messages": [], "attachments": []})

        messages = InboxMessage.objects.filter(
            user=user,
            conversation=conversation
        ).order_by("received_at")

        # 🔥 COLLECT ALL ATTACHMENTS
        all_attachments = []

        for msg in messages:
            for att in (msg.attachment_meta or []):
                all_attachments.append({
                    "message_id": msg.id,
                    "filename": att.get("filename"),
                    "attachment_id": att.get("attachment_id"),
                    "mime_type": att.get("mime_type"),
                })

        return Response({
            "messages": [
                {
                    "id": msg.id,
                    "sender": msg.sender,
                    "recipients": msg.recipients,
                    "direction": msg.direction,
                    "platform": msg.platform,
                    "subject": msg.subject or "No Subject",
                    "body": msg.body or "",
                    "time": msg.received_at,
                }
                for msg in messages
            ],
            "attachments": all_attachments
        })