from django.urls import path

from .views import (
    NotificationListAPIView,
    MarkNotificationReadAPIView,
    MarkAllNotificationsReadAPIView,
)

urlpatterns = [
    path("", NotificationListAPIView.as_view()),
    path(
        "<int:notification_id>/read/",
        MarkNotificationReadAPIView.as_view()
    ),
    path(
        "read-all/",
        MarkAllNotificationsReadAPIView.as_view()
    ),
]