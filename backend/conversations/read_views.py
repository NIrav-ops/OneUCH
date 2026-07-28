from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from inbox.models import InboxMessage


class MarkConversationReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):
        InboxMessage.objects.filter(
            conversation_id=conversation_id,
            user=request.user,
            is_read=False
        ).update(is_read=True)

        return Response({"status": "marked_read"})
