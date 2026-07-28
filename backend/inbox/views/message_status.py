from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from inbox.models import InboxMessage


class MessageStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, message_id):
        try:
            message = InboxMessage.objects.get(
                id=message_id,
                user=request.user,
            )
        except InboxMessage.DoesNotExist:
            return Response({"error": "Message not found"}, status=404)

        return Response({
            "id": message.id,
            "status": message.status,
            "retry_count": message.retry_count,
            "last_attempt_at": message.last_attempt_at,
            "error_reason": message.error_reason,
        })

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from inbox.models import InboxMessage


class BulkMessageStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        message_ids = request.data.get("message_ids", [])

        # ✅ Validate input
        if not isinstance(message_ids, list):
            return Response(
                {"error": "message_ids must be a list"},
                status=400
            )

        # ✅ Convert all IDs to int safely
        try:
            message_ids = [int(mid) for mid in message_ids]
        except ValueError:
            return Response(
                {"error": "message_ids must contain integers only"},
                status=400
            )

        # ✅ Filter securely by user
        messages = InboxMessage.objects.filter(
            user=request.user,
            id__in=message_ids,
        )

        return Response([
            {
                "id": msg.id,
                "status": msg.status,
                "retry_count": msg.retry_count,
                "last_attempt_at": msg.last_attempt_at,
                "error_reason": msg.error_reason,
            }
            for msg in messages
        ])