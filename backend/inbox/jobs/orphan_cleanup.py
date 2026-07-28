from inbox.models import Attachment
from inbox.audit import log_audit_event


def run():
    """
    Deletes attachments whose message no longer exists
    """
    count = 0

    orphans = Attachment.objects.filter(message__isnull=True)

    for attachment in orphans:
        attachment.file.delete(save=False)
        attachment.delete()

        log_audit_event(
            user=None,
            organization=None,
            action="ORPHAN_ATTACHMENT_DELETED",
            metadata={
                "attachment_id": attachment.id,
                "filename": attachment.filename,
            },
        )

        count += 1

    return count
