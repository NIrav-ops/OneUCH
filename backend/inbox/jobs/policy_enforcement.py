from inbox.models import Attachment
from inbox.audit import log_audit_event


def run():
    """
    Marks attachments that violate org attachment policy
    """
    count = 0

    attachments = (
        Attachment.objects
        .select_related(
            "message",
            "message__organization",
            "message__organization__attachment_policy",
        )
        .all()
    )

    for attachment in attachments:
        policy = attachment.message.organization.attachment_policy
        if not policy:
            continue

        size_mb = attachment.size / (1024 * 1024)

        if size_mb > policy.max_size_mb:
            if not attachment.policy_violated:
                attachment.policy_violated = True
                attachment.save(update_fields=["policy_violated"])

                log_audit_event(
                    user=None,
                    organization=attachment.message.organization,
                    action="ATTACHMENT_POLICY_VIOLATION",
                    metadata={
                        "attachment_id": attachment.id,
                        "size_mb": round(size_mb, 2),
                        "policy_limit_mb": policy.max_size_mb,
                    },
                )

                count += 1

    return count
