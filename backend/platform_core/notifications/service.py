from platform_core.notifications.repository import (
    NotificationRepository,
)


class NotificationService:

    def all(
        self,
    ):

        return NotificationRepository.all()

    def count(
        self,
    ):

        return NotificationRepository.count()

    def clear(
        self,
    ):

        NotificationRepository.clear()