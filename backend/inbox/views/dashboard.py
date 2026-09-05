from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from inbox.models import InboxMessage
from actions.models import ActionItem, FollowUpItem
from approvals.models import ApprovalItem
from timeline.models import TimelineEvent

from common.sla import calculate_sla

from platform_core.api.tenant import (
    get_user_organization_or_404,
)


class InboxDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        organization = (
            get_user_organization_or_404(
                request
            )
        )

        qs = InboxMessage.objects.filter(
            user=request.user,
            organization=organization,
        )

        # -------------------------
        # Work Counts
        # -------------------------

        assigned_actions = ActionItem.objects.filter(
            owner=request.user,
            organization=organization,
            status__in=[
                "open",
                "in_progress",
            ],
        ).count()

        pending_approvals = ApprovalItem.objects.filter(
            assigned_to=request.user,
            organization=organization,
            status="pending",
        ).count()

        pending_followups = FollowUpItem.objects.filter(
            user=request.user,
            organization=organization,
            status="pending",
        ).count()

        overdue_actions = ActionItem.objects.filter(
            owner=request.user,
            organization=organization,
            escalation_level__gt=0,
        ).count()

        # -------------------------
        # SLA ENGINE
        # -------------------------

        healthy = 0
        warning = 0
        breached = 0

        actions = ActionItem.objects.filter(
            owner=request.user,
            organization=organization,
        ).exclude(
            status="completed"
        )

        for action in actions:

            sla = calculate_sla(
                action.due_date,
                action.status,
            )

            if sla == "green":
                healthy += 1
            elif sla == "yellow":
                warning += 1
            else:
                breached += 1

        approvals = ApprovalItem.objects.filter(
            assigned_to=request.user,
            organization=organization,
        ).exclude(
            status__in=[
                "approved",
                "ignored",
            ]
        )

        for approval in approvals:

            sla = calculate_sla(
                approval.due_date,
                approval.status,
            )

            if sla == "green":
                healthy += 1
            elif sla == "yellow":
                warning += 1
            else:
                breached += 1

        followups = FollowUpItem.objects.filter(
            user=request.user,
            organization=organization,
            status="pending",
        )

        for followup in followups:

            sla = calculate_sla(
                followup.followup_due_at,
                followup.status,
            )

            if sla == "green":
                healthy += 1
            elif sla == "yellow":
                warning += 1
            else:
                breached += 1

        # -------------------------
        # Timeline Feed
        # -------------------------

        recent_events = (
            TimelineEvent.objects.filter(
                conversation__user=request.user,
                conversation__organization=organization,
            )
            .order_by("-created_at")[:10]
        )

        recent_activity = []

        for event in recent_events:

            recent_activity.append({
                "id": event.id,
                "title": event.title,
                "event_type": event.event_type,
                "created_at": event.created_at,
                "details": event.details,
            })

        # -------------------------
        # Productivity Metrics
        # -------------------------

        completed_actions = ActionItem.objects.filter(
            owner=request.user,
            organization=organization,
            status="completed",
        ).count()

        approved_items = ApprovalItem.objects.filter(
            assigned_to=request.user,
            organization=organization,
            status="approved",
        ).count()

        # -------------------------
        # Platform Analytics
        # -------------------------

        gmail_count = qs.filter(
            platform="gmail"
        ).count()

        outlook_count = qs.filter(
            platform="outlook"
        ).count()

        total_platform_messages = (
            gmail_count +
            outlook_count
        )

        gmail_percentage = 0
        outlook_percentage = 0

        if total_platform_messages > 0:

            gmail_percentage = round(
                (gmail_count / total_platform_messages) * 100,
                1
            )

            outlook_percentage = round(
                (outlook_count / total_platform_messages) * 100,
                1
            )

        # -------------------------
        # Response
        # -------------------------

        return Response({

            # Inbox

            "total_messages": qs.count(),

            "unread": qs.filter(
                is_read=False
            ).count(),

            "gmail": gmail_count,

            "outlook": outlook_count,

            "imap": qs.filter(
                platform="imap"
            ).count(),

            "teams": qs.filter(
                platform="teams"
            ).count(),

            # Work

            "assigned_actions": assigned_actions,

            "pending_approvals": pending_approvals,

            "pending_followups": pending_followups,

            "overdue_actions": overdue_actions,

            # SLA

            "sla_healthy": healthy,

            "sla_warning": warning,

            "sla_breached": breached,

            # Productivity

            "completed_actions": completed_actions,

            "approved_items": approved_items,

            # Analytics

            "gmail_percentage": gmail_percentage,

            "outlook_percentage": outlook_percentage,

            # Timeline

            "recent_activity": recent_activity,

        })