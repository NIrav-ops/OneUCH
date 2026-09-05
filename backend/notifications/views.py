from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer

from platform_core.api.tenant import (
    get_user_organization_or_404,
)


class NotificationListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        organization = (
            get_user_organization_or_404(
                request
            )
        )

        notifications = (
            Notification.objects
            .filter(
                user=request.user,
                organization=organization,
            )
            .order_by("-created_at")
        )

        serializer = NotificationSerializer(
            notifications,
            many=True,
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

    def post(
        self,
        request,
        notification_id,
    ):

        organization = (
            get_user_organization_or_404(
                request
            )
        )

        try:
            notification = (
                Notification.objects.get(
                    id=notification_id,
                    user=request.user,
                    organization=organization,
                )
            )

        except Notification.DoesNotExist:
            return Response(
                {
                    "error": "Not found"
                },
                status=404,
            )

        notification.is_read = True

        notification.save(
            update_fields=[
                "is_read"
            ]
        )

        return Response({
            "status": "read"
        })


class MarkAllNotificationsReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        organization = (
            get_user_organization_or_404(
                request
            )
        )

        Notification.objects.filter(
            user=request.user,
            organization=organization,
            is_read=False,
        ).update(
            is_read=True
        )

        return Response({
            "status": "all_read"
        })
