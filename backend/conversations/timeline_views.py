from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from inbox.models import Conversation
from inbox.models import InboxMessage


class ConversationTimelineAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        conversation = Conversation.objects.filter(
            id=conversation_id,
            user=request.user
        ).first()

        if not conversation:
            return Response(
                {"detail": "Conversation not found"},
                status=404
            )

        messages = InboxMessage.objects.filter(
            conversation=conversation
        ).order_by("received_at")

        timeline = []
        for msg in messages:
            timeline.append({
                "id": msg.id,
                "direction": msg.direction,
                "platform": msg.platform,
                "sender": msg.sender,
                "recipients": msg.recipients,
                "subject": msg.subject,
                "body": msg.body,
                "status": msg.status,
                "received_at": msg.received_at,
                "attachments": [
                    {
                    "id": att.id,
                    "filename": att.filename,
                    "content_type": att.content_type,
                    "size": att.size,
                    }
                    for att in msg.attachments.all()
                ]
            })

        return Response({
            "conversation_id": conversation.id,
            "subject": conversation.subject,
            "participants": conversation.participants,
            "count": len(timeline),
            "messages": timeline
        })
