from notifications.models import Notification


def create_notification(*, user, type, title, message):
    Notification.objects.create(
        user=user,
        type=type,
        title=title,
        message=message,
    )