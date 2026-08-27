from celery import shared_task
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from notifications.services import create_notification
from actions.models import ActionItem
from approvals.models import ApprovalItem
from actions.models import FollowUpItem


def should_send_reminder(last_sent_at, now, interval_hours=24):
    if not last_sent_at:
        return True
    return last_sent_at <= now - timedelta(hours=interval_hours)


@shared_task
def scan_overdue_work_and_notify():
    now = timezone.now()
    cutoff = now - timedelta(hours=24)

    created_count = 0

    # --------------------
    # Overdue Actions
    # --------------------
    overdue_actions = ActionItem.objects.select_related("owner", "user").filter(
        status="open",
        due_date__isnull=False,
        due_date__lt=now,
    )

    for action in overdue_actions:
        recipient = action.owner or action.user
        if not recipient:
            continue

        if not should_send_reminder(action.last_reminder_sent_at, now):
            continue

        title = f"Overdue action: {action.title}"
        message = (
            f"Your action is overdue in One UCH.\n\n"
            f"Title: {action.title}\n"
            f"Due date: {action.due_date}\n"
            f"Priority: {action.priority}\n\n"
            f"Please review it in the Action Center."
        )

        create_notification(
            user=recipient,
            type="overdue_action",
            title=title,
            message=message,
        )

        if recipient.email:
            send_mail(
                subject=title,
                message=message,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                recipient_list=[recipient.email],
                fail_silently=True,
            )

        action.last_reminder_sent_at = now
        action.save(update_fields=["last_reminder_sent_at"])
        created_count += 1

    # --------------------
    # Overdue Approvals
    # --------------------
    overdue_approvals = ApprovalItem.objects.select_related("assigned_to", "user").filter(
        status="pending",
        due_date__isnull=False,
        due_date__lt=now,
    )

    for approval in overdue_approvals:
        recipient = approval.assigned_to or approval.user
        if not recipient:
            continue

        if not should_send_reminder(approval.last_reminder_sent_at, now):
            continue

        title = f"Overdue approval: {approval.title}"
        message = (
            f"An approval is overdue in One UCH.\n\n"
            f"Title: {approval.title}\n"
            f"Due date: {approval.due_date}\n"
            f"Status: {approval.status}\n\n"
            f"Please review it in the Approval Center."
        )

        create_notification(
            user=recipient,
            type="overdue_approval",
            title=title,
            message=message,
        )

        if recipient.email:
            send_mail(
                subject=title,
                message=message,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                recipient_list=[recipient.email],
                fail_silently=True,
            )

        approval.last_reminder_sent_at = now
        approval.save(update_fields=["last_reminder_sent_at"])
        created_count += 1

    # --------------------
    # Overdue Follow-ups
    # --------------------
    overdue_followups = FollowUpItem.objects.select_related("user").filter(
        status="pending",
        followup_due_at__isnull=False,
        followup_due_at__lt=now,
    )

    for followup in overdue_followups:
        recipient = followup.user
        if not recipient:
            continue

        if not should_send_reminder(followup.last_reminder_sent_at, now):
            continue

        subject_text = "Overdue follow-up"
        try:
            if followup.last_message and followup.last_message.subject:
                subject_text = followup.last_message.subject
        except Exception:
            pass

        title = f"Follow-up overdue: {subject_text}"
        message = (
            f"A follow-up is overdue in One UCH.\n\n"
            f"Subject: {subject_text}\n"
            f"Due date: {followup.followup_due_at}\n\n"
            f"Please review it in the Dashboard or Inbox."
        )

        create_notification(
            user=recipient,
            type="overdue_followup",
            title=title,
            message=message,
        )

        if recipient.email:
            send_mail(
                subject=title,
                message=message,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                recipient_list=[recipient.email],
                fail_silently=True,
            )

        followup.last_reminder_sent_at = now
        followup.save(update_fields=["last_reminder_sent_at"])
        created_count += 1

    return created_count
# Ensure escalation task is registered by Celery autodiscovery.
from notifications.tasks_escalation import run_escalation_engine  # noqa: F401
