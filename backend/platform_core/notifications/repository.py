class NotificationRepository:
    """
    Temporary repository.

    Phase 11 will replace this with
    notifications.models.Notification
    """

    _notifications = []

    @classmethod
    def save(
        cls,
        notification,
    ):

        cls._notifications.append(
            notification,
        )

    @classmethod
    def all(
        cls,
    ):

        return list(
            cls._notifications,
        )

    @classmethod
    def clear(
        cls,
    ):

        cls._notifications.clear()

    @classmethod
    def count(
        cls,
    ):

        return len(
            cls._notifications,
        )