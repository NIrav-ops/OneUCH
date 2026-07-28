from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from inbox.models import Conversation
from inbox.reply_service import send_reply


class ConversationReplyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):
        body = request.data.get("body")

        if not body:
            return Response(
                {"error": "Message body is required"},
                status=400
            )

        conversation = get_object_or_404(
            Conversation,
            id=conversation_id,
            user=request.user
        )

        msg = send_reply(
            user=request.user,
            conversation=conversation,
            body=body,
        )

        return Response({
            "status": "sent",
            "message_id": msg.id
        })
