from celery import shared_task

from inbox.models import InboxMessage
from actions.models import (
    ActionItem,
    FollowUpItem,
)

from actions.services.extractor import (
    extract_actions,
    detect_followup,
)

from timeline.services import (
    create_timeline_event,
)


@shared_task
def analyze_new_messages():

    messages = InboxMessage.objects.filter(
        action_analyzed=False,
        is_draft=False,
    ).select_related(
        "conversation",
        "organization",
        "user",
    )

    processed_count = 0

    for msg in messages:

        subject = msg.subject or ""
        body = msg.body or ""

        actions = extract_actions(
            subject,
            body,
        )

        followup = detect_followup(
            subject,
            body,
        )

        # ---------------------
        # ACTIONS
        # ---------------------

        for item in actions:

            action_obj, created = (
                ActionItem.objects.get_or_create(
                    message=msg,
                    title=item["title"],
                    defaults={
                        "user": msg.user,
                        "organization": msg.organization,
                        "description": item.get(
                            "description",
                            "",
                        ),
                        "priority": item.get(
                            "priority",
                            0,
                        ),
                        "confidence_score": item.get(
                            "confidence_score",
                            0,
                        ),
                    },
                )
            )

            if created and msg.conversation:

                create_timeline_event(
                    conversation=msg.conversation,
                    event_type="action_created",
                    title="Action generated",
                    details={
                        "action_id": action_obj.id,
                        "action_title": action_obj.title,
                    },
                )

        # ---------------------
        # FOLLOWUPS
        # ---------------------

        if followup and msg.conversation:

            followup_obj, created = (
                FollowUpItem.objects.get_or_create(
                    conversation=msg.conversation,
                    last_message=msg,
                    defaults={
                        "user": msg.user,
                        "organization": msg.organization,
                        "followup_due_at":
                            followup[
                                "followup_due_at"
                            ],
                    },
                )
            )

            if created:

                create_timeline_event(
                    conversation=msg.conversation,
                    event_type="followup_created",
                    title="Followup scheduled",
                    details={
                        "followup_id":
                            followup_obj.id,
                        "due_date": str(
                            followup_obj.followup_due_at
                        ),
                    },
                )

        msg.action_analyzed = True

        msg.save(
            update_fields=[
                "action_analyzed"
            ]
        )

        processed_count += 1

    return processed_count