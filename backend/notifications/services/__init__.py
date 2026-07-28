from .repository import NotificationRepository


def create_notification(**kwargs):
    """
    Backward-compatible helper for existing code.

    New code should use NotificationRepository or
    NotificationIntegrationService directly.
    """
    return NotificationRepository.create_notification(**kwargs)