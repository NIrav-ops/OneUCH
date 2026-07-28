from django.db import transaction

from notifications.models import Notification
from notifications.services.base_repository import BaseRepository
from notifications.services.validator import NotificationValidator


class NotificationRepository(BaseRepository):

    model = Notification

    @classmethod
    @transaction.atomic
    def create_notification(cls, **data):

        NotificationValidator.validate_create(data)

        data.setdefault(
            "channel",
            "in_app",
        )

        data.setdefault(
            "status",
            "pending",
        )

        data.setdefault(
            "source_type",
            "system",
        )

        return cls.create(**data)

    @classmethod
    def mark_sent(cls, notification):

        notification.status = "sent"

        notification.save(
            update_fields=["status"]
        )

        return notification

    @classmethod
    def mark_failed(cls, notification):

        notification.status = "failed"

        notification.save(
            update_fields=["status"]
        )

        return notification

    @classmethod
    def mark_read(cls, notification):

        notification.is_read = True

        notification.save(
            update_fields=["is_read"]
        )

        return notification

    @classmethod
    def mark_unread(cls, notification):

        notification.is_read = False

        notification.save(
            update_fields=["is_read"]
        )

        return notification

    @classmethod
    def get_unread(cls, user):

        return cls.model.objects.filter(
            user=user,
            is_read=False,
        )

    @classmethod
    def get_pending(cls):

        return cls.model.objects.filter(
            status="pending",
        )

    @classmethod
    def get_failed(cls):

        return cls.model.objects.filter(
            status="failed",
        )