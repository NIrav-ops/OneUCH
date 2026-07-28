from django.utils import timezone
from .models import TimelineEvent


def create_timeline_event(
    conversation,
    event_type,
    title,
    details=None,
    event_at=None,
):

    if details is None:
        details = {}

    return TimelineEvent.objects.create(
        conversation=conversation,
        event_type=event_type,
        title=title,
        details=details,
        event_at=event_at or timezone.now(),
    )