from celery import shared_task
from django.utils import timezone
from datetime import timedelta

from actions.models import ActionItem, FollowUpItem
from approvals.models import ApprovalItem

from notifications.services import create_notification


@shared_task
def run_escalation_engine():

    now = timezone.now()

    process_actions(now)
    process_approvals(now)
    process_followups(now)

    return "Escalation completed"


def process_actions(now):

    actions = ActionItem.objects.filter(
        status__in=["open", "in_progress"],
        due_date__isnull=False,
    )

    for action in actions:

        overdue_hours = (
            now - action.due_date
        ).total_seconds() / 3600

        if overdue_hours >= 24 and action.escalation_level == 0:

            create_notification(
                user=action.user,
                type="escalation_level_1",
                title=f"Action Escalated: {action.title}",
                message="Action overdue for 24 hours."
            )

            action.escalation_level = 1
            action.save()

        elif overdue_hours >= 48 and action.escalation_level == 1:

            create_notification(
                user=action.user,
                type="escalation_level_2",
                title=f"Action Escalated: {action.title}",
                message="Action overdue for 48 hours."
            )

            action.escalation_level = 2
            action.save()

        elif overdue_hours >= 72 and action.escalation_level == 2:

            create_notification(
                user=action.user,
                type="escalation_level_3",
                title=f"Action Escalated: {action.title}",
                message="Action overdue for 72 hours."
            )

            action.escalation_level = 3
            action.save()


def process_approvals(now):

    approvals = ApprovalItem.objects.filter(
        status="pending",
        due_date__isnull=False,
    )

    for approval in approvals:

        overdue_hours = (
            now - approval.due_date
        ).total_seconds() / 3600

        if overdue_hours >= 24 and approval.escalation_level == 0:

            create_notification(
                user=approval.user,
                type="escalation_level_1",
                title=f"Approval Escalated: {approval.title}",
                message="Approval overdue for 24 hours."
            )

            approval.escalation_level = 1
            approval.save()

        elif overdue_hours >= 48 and approval.escalation_level == 1:

            create_notification(
                user=approval.user,
                type="escalation_level_2",
                title=f"Approval Escalated: {approval.title}",
                message="Approval overdue for 48 hours."
            )

            approval.escalation_level = 2
            approval.save()

        elif overdue_hours >= 72 and approval.escalation_level == 2:

            create_notification(
                user=approval.user,
                type="escalation_level_3",
                title=f"Approval Escalated: {approval.title}",
                message="Approval overdue for 72 hours."
            )

            approval.escalation_level = 3
            approval.save()


def process_followups(now):

    followups = FollowUpItem.objects.filter(
        status="pending",
        followup_due_at__isnull=False,
    )

    for item in followups:

        overdue_hours = (
            now - item.followup_due_at
        ).total_seconds() / 3600

        if overdue_hours >= 24 and item.escalation_level == 0:

            create_notification(
                user=item.user,
                type="escalation_level_1",
                title="Follow-up Escalated",
                message="Follow-up overdue for 24 hours."
            )

            item.escalation_level = 1
            item.save()