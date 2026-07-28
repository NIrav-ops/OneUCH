from datetime import timedelta
from django.utils import timezone

from inbox.models import AuditLog


def run(days_to_keep=90):
    """
    Deletes audit logs older than `days_to_keep`
    """
    cutoff = timezone.now() - timedelta(days=days_to_keep)

    deleted_count, _ = AuditLog.objects.filter(
        created_at__lt=cutoff
    ).delete()

    return deleted_count
