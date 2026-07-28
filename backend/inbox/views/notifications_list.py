from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from inbox.models import Notification


class NotificationListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = (
            Notification.objects
            .filter(user=request.user)
            .order_by("-created_at")[:50]
        )

        data = [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "type": n.notification_type,
                "is_read": n.is_read,
                "created_at": n.created_at,
            }
            for n in notifications
        ]

        return Response(data)
