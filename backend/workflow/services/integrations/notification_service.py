from notifications.services.repository import NotificationRepository


class NotificationIntegrationService:
    """
    Workflow -> Notification integration.

    Workflow never talks directly to Notification models.
    Everything goes through this service.
    """

    @classmethod
    def create_notification(
        cls,
        *,
        organization,
        title,
        message,
        notification_type="system",
        user=None,
        workflow_instance=None,
        workflow_node=None,
        channel="in_app",
        metadata=None,
    ):
        """
        Create a workflow notification.
        """

        return NotificationRepository.create_notification(
            organization=organization,
            user=user,
            title=title,
            message=message,
            type=notification_type,
            channel=channel,
            source_type="workflow",
            workflow_instance=workflow_instance,
            workflow_node=workflow_node,
            metadata=metadata or {},
        )

    @classmethod
    def mark_sent(cls, notification):
        return NotificationRepository.mark_sent(notification)

    @classmethod
    def mark_failed(cls, notification):
        return NotificationRepository.mark_failed(notification)

    @classmethod
    def mark_read(cls, notification):
        return NotificationRepository.mark_read(notification)

    @classmethod
    def mark_unread(cls, notification):
        return NotificationRepository.mark_unread(notification)