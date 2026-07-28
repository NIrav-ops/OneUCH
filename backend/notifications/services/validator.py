from notifications.exceptions import InvalidNotification
from notifications.models import Notification


class NotificationValidator:

    @classmethod
    def validate_create(cls, data):
        """
        Validate Notification creation payload.
        """

        required = [
            "organization",
            "title",
            "message",
            "type",
        ]

        for field in required:
            value = data.get(field)

            if value is None:
                raise InvalidNotification(f"{field} is required")

            if isinstance(value, str) and not value.strip():
                raise InvalidNotification(f"{field} cannot be blank")

        # ----------------------------------------------------
        # Validate Notification Type
        # ----------------------------------------------------

        valid_types = {
            value
            for value, _ in Notification.NOTIFICATION_TYPES
        }

        if data["type"] not in valid_types:
            raise InvalidNotification(
                f"Invalid notification type: {data['type']}"
            )

        # ----------------------------------------------------
        # Validate Channel
        # ----------------------------------------------------

        channel = data.get("channel", "in_app")

        valid_channels = {
            value
            for value, _ in Notification.CHANNEL_TYPES
        }

        if channel not in valid_channels:
            raise InvalidNotification(
                f"Invalid notification channel: {channel}"
            )

        # ----------------------------------------------------
        # Validate Source
        # ----------------------------------------------------

        source = data.get("source_type", "system")

        valid_sources = {
            value
            for value, _ in Notification.SOURCE_TYPES
        }

        if source not in valid_sources:
            raise InvalidNotification(
                f"Invalid source type: {source}"
            )

        # ----------------------------------------------------
        # Workflow Notifications
        # ----------------------------------------------------

        if source == "workflow":

            if not data.get("workflow_instance"):
                raise InvalidNotification(
                    "workflow_instance is required"
                )   