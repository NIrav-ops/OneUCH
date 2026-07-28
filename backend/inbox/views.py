from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from django.db.models import Max, Count, Q

from .models import InboxMessage, Conversation


# =========================
# 🔥 LEFT PANEL (INBOX/SENT/DRAFT)
# =========================
class UnifiedConversationInboxAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):

        user = request.user
        folder = request.GET.get("folder", "inbox")

        # =========================
        # FILTER BY FOLDER
        # =========================
        if folder == "sent":
            messages = InboxMessage.objects.filter(
                user=user,
                direction="outbound",
                is_draft=False
            )
        elif folder == "draft":
            messages = InboxMessage.objects.filter(
                user=user,
                is_draft=True
            )
        else:
            messages = InboxMessage.objects.filter(
                user=user,
                direction="inbound",
                is_draft=False
            )

        # =========================
        # GROUP BY CONVERSATION
        # =========================
        conversations = (
            messages
            .select_related("conversation")
            .values("conversation")
            .annotate(
                last_message_time=Max("received_at"),
                unread_count=Count("id", filter=Q(is_read=False))
            )
            .order_by("-last_message_time")
        )

        results = []

        for item in conversations:
            conv_id = item["conversation"]

            last_msg = InboxMessage.objects.filter(
                conversation_id=conv_id
            ).order_by("-received_at").first()

            if not last_msg:
                continue

            results.append({
                "conversation_id": conv_id,
                "subject": last_msg.subject or "No Subject",
                "preview": (last_msg.body[:120] if last_msg.body else ""),
                "platform": last_msg.platform,
                "last_message_time": last_msg.received_at,
                "unread_count": item["unread_count"],
            })

        return Response({
            "results": results
        }, status=status.HTTP_200_OK)


# =========================
# 🔥 RIGHT PANEL (THREAD VIEW)
# =========================
class ConversationDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):

        print("🔥 NEW CONVERSATION API HIT 🔥")

        user = request.user

        print("\n======================")
        print("CLICKED CONVERSATION ID:", conversation_id)

        try:
            conversation = Conversation.objects.get(id=conversation_id)
            print("THREAD KEY:", conversation.conversation_key)
        except Conversation.DoesNotExist:
            print("❌ Conversation not found")
            return Response({"messages": []})

        messages = InboxMessage.objects.filter(
            user=user,
            conversation=conversation
        ).order_by("received_at")

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
            "messages": [...],
            "attachments": all_attachments
        })