from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth import get_user_model

from inbox.models import InboxMessage
from notifications.services import create_notification
from approvals.models import ApprovalItem
from timeline.services import create_timeline_event
from approvals.services.extractor import (
    extract_approvals,
    detect_approval_followup,
)

User = get_user_model()


@shared_task
def analyze_new_approvals():

    messages = InboxMessage.objects.filter(
        approval_analyzed=False,
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

        approvals = extract_approvals(
            subject,
            body,
        )

        followup_due = detect_approval_followup(
            subject,
            body,
        )

        for item in approvals:

            approval_obj, created = (
                ApprovalItem.objects.get_or_create(
                    message=msg,
                    title=item["title"],
                    defaults={
                        "user": msg.user,
                        "organization": msg.organization,
                        "conversation": msg.conversation,
                        "description": item.get(
                            "description",
                            "",
                        ),
                        "requested_by": msg.sender,
                        "status": "pending",
                        "confidence_score": item.get(
                            "confidence_score",
                            0,
                        ),
                        "due_date": item.get(
                            "due_date"
                        ),
                    },
                )
            )

            if created and msg.conversation:

                create_timeline_event(
                    conversation=msg.conversation,
                    event_type="approval_created",
                    title="Approval created",
                    details={
                        "approval_id": approval_obj.id,
                        "title": approval_obj.title,
                    },
                )

        if followup_due and msg.conversation:

            ApprovalItem.objects.filter(
                message=msg
            ).update(
                due_date=followup_due
            )

        msg.approval_analyzed = True

        msg.save(
            update_fields=[
                "approval_analyzed"
            ]
        )

        processed_count += 1

    return processed_count


@shared_task
def send_approval_assignment_notification(
    approval_id,
    assignee_id,
    assigned_by_id,
):

    try:

        approval = (
            ApprovalItem.objects
            .select_related(
                "organization"
            )
            .get(
                id=approval_id
            )
        )

        assignee = User.objects.get(
            id=assignee_id
        )

        assigned_by = User.objects.get(
            id=assigned_by_id
        )

    except Exception as exc:

        return {
            "status": "error",
            "error": str(exc),
        }

    subject = (
        f"New approval assigned: "
        f"{approval.title}"
    )

    message = (
        f"You have been assigned an approval in One UCH.\n\n"
        f"Title: {approval.title}\n"
        f"Organization: {approval.organization.name}\n"
        f"Requested by: {approval.requested_by or 'Unknown'}\n"
        f"Assigned by: {assigned_by.email}\n"
        f"Status: {approval.status}\n\n"
        f"Please review it in the Approval Center."
    )

    create_notification(
        user=assignee,
        type="approval_assigned",
        title=subject,
        message=message,
    )

    if assignee.email:

        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(
                settings,
                "DEFAULT_FROM_EMAIL",
                None,
            ),
            recipient_list=[
                assignee.email
            ],
            fail_silently=True,
        )

    return {
        "status": "sent"
    }