from django.utils import timezone
from inbox.models import InboxSyncStatus


def update_sync_status(
    *,
    user,
    platform,
    status,
    progress=0,
    error_message="",
):
    obj, _ = InboxSyncStatus.objects.get_or_create(
        user=user,
        platform=platform,
    )

    obj.status = status
    obj.progress = progress
    obj.error_message = error_message

    if status == "success":
        obj.last_synced_at = timezone.now()

    obj.save()
    return obj
