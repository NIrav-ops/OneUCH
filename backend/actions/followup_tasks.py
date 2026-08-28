from celery import shared_task

from inbox.models import InboxMessage

from actions.models import FollowUpItem
from actions.services.extractor import detect_followup

from knowledge.services.intelligence_evidence_persistence import (
    persist_intelligence_evidence,
)


@shared_task
def analyze_new_followups(
    message_ids=None,
):
    """
    Analyze inbound, non-draft messages for explicit
    deterministic follow-up obligations.
    """

    messages = InboxMessage.objects.filter(
        followup_analyzed=False,
        is_draft=False,
        direction="inbound",
    )

    if message_ids is not None:
        messages = messages.filter(
            id__in=message_ids
        )

    messages = messages.select_related(
        "conversation",
        "organization",
        "user",
    )

    processed_count = 0

    for msg in messages:
        subject = msg.subject or ""
        body = msg.body or ""

        result = detect_followup(
            subject,
            body,
            reference_time=msg.received_at,
        )

        if result and msg.conversation:
            existing = (
                FollowUpItem.objects.filter(
                    conversation=msg.conversation,
                    status="pending",
                )
                .order_by("-created_at")
                .first()
            )

            if existing:
                existing.last_message = msg
                existing.user = msg.user
                existing.organization = (
                    msg.organization
                )

                explicit_due_at = result.get(
                    "followup_due_at"
                )

                if explicit_due_at is not None:
                    existing.followup_due_at = (
                        explicit_due_at
                    )

                existing.save(
                    update_fields=[
                        "last_message",
                        "user",
                        "organization",
                        "followup_due_at",
                    ]
                )

                followup_item = existing

            else:
                followup_item = (
                    FollowUpItem.objects.create(
                        conversation=(
                            msg.conversation
                        ),
                        last_message=msg,
                        user=msg.user,
                        organization=(
                            msg.organization
                        ),
                        followup_due_at=(
                            result.get(
                                "followup_due_at"
                            )
                        ),
                        status="pending",
                    )
                )

            persist_intelligence_evidence(
                followup_item,
                evidence_text=(
                    result.get(
                        "evidence_text"
                    )
                    or ""
                ),
                extraction_method=(
                    "deterministic"
                ),
                processing_mode=(
                    "deterministic"
                ),
                provider=None,
                model=None,
                confidence=100,
            )

        msg.followup_analyzed = True

        msg.save(
            update_fields=[
                "followup_analyzed"
            ]
        )

        processed_count += 1

    return processed_count
