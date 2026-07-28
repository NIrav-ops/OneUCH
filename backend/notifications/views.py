from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer


class NotificationListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        notifications = (
            Notification.objects
            .filter(user=request.user)
            .order_by("-created_at")
        )

        serializer = NotificationSerializer(
            notifications,
            many=True
        )

        unread_count = notifications.filter(
            is_read=False
        ).count()

        return Response({
            "unread_count": unread_count,
            "notifications": serializer.data,
        })


class MarkNotificationReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, notification_id):

        try:
            notification = Notification.objects.get(
                id=notification_id,
                user=request.user,
            )

            notification.is_read = True
            notification.save()

            return Response({
                "status": "read"
            })

        except Notification.DoesNotExist:
            return Response(
                {"error": "Not found"},
                status=404
            )


class MarkAllNotificationsReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(
            is_read=True
        )

        return Response({
            "status": "all_read"
        })