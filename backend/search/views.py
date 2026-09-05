from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from django.db.models import Q

from inbox.models import (
    InboxMessage,
    Conversation,
)

from actions.models import (
    ActionItem,
    FollowUpItem,
)

from approvals.models import ApprovalItem
from timeline.models import TimelineEvent

from platform_core.api.tenant import (
    get_user_organization_or_404,
)


class UnifiedSearchAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        organization = (
            get_user_organization_or_404(
                request
            )
        )

        q = request.GET.get(
            "q",
            ""
        ).strip()

        if not q:
            return Response(
                {
                    "query": "",
                    "count": 0,
                    "results": [],
                    "grouped": {
                        "messages": [],
                        "actions": [],
                        "approvals": [],
                        "followups": [],
                        "timeline": [],
                        "conversations": [],
                    },
                },
                status=status.HTTP_200_OK,
            )

        message_results = []
        action_results = []
        approval_results = []
        followup_results = []
        timeline_results = []
        conversation_results = []

        # =====================================================
        # EMAILS
        # =====================================================

        messages = (
            InboxMessage.objects.filter(
                user=request.user,
                organization=organization,
            )
            .filter(
                Q(subject__icontains=q)
                | Q(sender__icontains=q)
                | Q(body__icontains=q)
                | Q(recipients__icontains=q)
            )
            .order_by("-received_at")[:10]
        )

        for msg in messages:

            message_results.append(
                {
                    "type": "message",
                    "id": msg.id,
                    "title": msg.subject
                    or "No Subject",
                    "subtitle": msg.sender
                    or "Unknown",
                    "preview": (
                        msg.body or ""
                    )[:160],
                    "url":
                    (
                        f"/inbox?"
                        f"conversation="
                        f"{msg.conversation_id}"
                    )
                    if msg.conversation_id
                    else "/inbox",
                    "timestamp":
                    msg.received_at,
                    "meta": {
                        "platform":
                        msg.platform,
                        "folder":
                        msg.folder,
                        "status":
                        msg.status,
                    },
                }
            )

        # =====================================================
        # ACTIONS
        # =====================================================

        actions = (
            ActionItem.objects.filter(
                user=request.user,
                organization=organization,
            )
            .filter(
                Q(title__icontains=q)
                | Q(description__icontains=q)
                | Q(owner__email__icontains=q)
            )
            .select_related(
                "owner"
            )
            .order_by("-created_at")[:10]
        )

        for action in actions:

            action_results.append(
                {
                    "type": "action",
                    "id": action.id,
                    "title": action.title,
                    "subtitle":
                    (
                        action.owner.email
                        if action.owner
                        else "Unassigned"
                    ),
                    "preview":
                    (
                        action.description
                        or ""
                    )[:160],
                    "url": "/actions",
                    "timestamp":
                    action.created_at,
                    "meta": {
                        "status":
                        action.status,
                        "priority":
                        action.priority,
                        "due_date":
                        action.due_date,
                    },
                }
            )

        # =====================================================
        # APPROVALS
        # =====================================================

        approvals = (
            ApprovalItem.objects.filter(
                user=request.user,
                organization=organization,
            )
            .filter(
                Q(title__icontains=q)
                | Q(description__icontains=q)
                | Q(requested_by__icontains=q)
                | Q(decision_notes__icontains=q)
                | Q(
                    assigned_to__email__icontains=q
                )
            )
            .select_related(
                "assigned_to"
            )
            .order_by("-created_at")[:10]
        )

        for approval in approvals:

            approval_results.append(
                {
                    "type": "approval",
                    "id": approval.id,
                    "title": approval.title,
                    "subtitle":
                    (
                        approval.assigned_to.email
                        if approval.assigned_to
                        else "Unassigned"
                    ),
                    "preview":
                    (
                        approval.description
                        or approval.decision_notes
                        or ""
                    )[:160],
                    "url": "/approvals",
                    "timestamp":
                    approval.created_at,
                    "meta": {
                        "status":
                        approval.status,
                        "confidence_score":
                        approval.confidence_score,
                        "due_date":
                        approval.due_date,
                    },
                }
            )

        # =====================================================
        # FOLLOWUPS
        # =====================================================

        followups = (
            FollowUpItem.objects.filter(
                user=request.user,
                organization=organization,
            )
            .filter(
                Q(
                    last_message__subject__icontains=q
                )
                | Q(
                    last_message__sender__icontains=q
                )
                | Q(
                    last_message__body__icontains=q
                )
            )
            .select_related(
                "conversation",
                "last_message",
            )
            .order_by("followup_due_at")[:10]
        )

        for followup in followups:

            subject = (
                followup.last_message.subject
                if (
                    followup.last_message
                    and followup.last_message.subject
                )
                else "No Subject"
            )

            sender = (
                followup.last_message.sender
                if (
                    followup.last_message
                    and followup.last_message.sender
                )
                else "Unknown"
            )

            preview = (
                followup.last_message.body[:160]
                if (
                    followup.last_message
                    and followup.last_message.body
                )
                else ""
            )

            followup_results.append(
                {
                    "type": "followup",
                    "id": followup.id,
                    "title": subject,
                    "subtitle": sender,
                    "preview": preview,
                    "url":
                    (
                        f"/inbox?"
                        f"conversation="
                        f"{followup.conversation_id}"
                    )
                    if followup.conversation_id
                    else "/inbox",
                    "timestamp":
                    followup.followup_due_at,
                    "meta": {
                        "status":
                        followup.status,
                    },
                }
            )

        # =====================================================
        # TIMELINE
        # =====================================================

        timeline_events = (
            TimelineEvent.objects.filter(
                conversation__user=request.user,
                conversation__organization=organization,
            )
            .filter(
                Q(title__icontains=q)
            )
            .order_by("-created_at")[:10]
        )

        for event in timeline_events:

            timeline_results.append(
                {
                    "type": "timeline",
                    "id": event.id,
                    "title": event.title,
                    "subtitle":
                    event.event_type,
                    "preview": "",
                    "url":
                    (
                        f"/inbox?"
                        f"conversation="
                        f"{event.conversation_id}"
                    ),
                    "timestamp":
                    (
                        event.event_at
                        or event.created_at
                    ),
                    "meta": {},
                }
            )

        # =====================================================
        # CONVERSATIONS
        # =====================================================

        conversations = (
            Conversation.objects.filter(
                user=request.user,
                organization=organization,
            )
            .filter(
                Q(subject__icontains=q)
            )
            .order_by("-last_message_at")[:10]
        )

        for conv in conversations:

            conversation_results.append(
                {
                    "type": "conversation",
                    "id": conv.id,
                    "title":
                    conv.subject
                    or "No Subject",
                    "subtitle":
                    "Conversation",
                    "preview": "",
                    "url":
                    (
                        f"/inbox?"
                        f"conversation="
                        f"{conv.id}"
                    ),
                    "timestamp":
                    conv.last_message_at,
                    "meta": {},
                }
            )

        # =====================================================
        # COMBINED RESULTS
        # =====================================================

        results = (
            message_results
            + action_results
            + approval_results
            + followup_results
            + timeline_results
            + conversation_results
        )

        return Response(
            {
                "query": q,
                "count": len(results),
                "results": results,
                "grouped": {
                    "messages":
                    message_results,
                    "actions":
                    action_results,
                    "approvals":
                    approval_results,
                    "followups":
                    followup_results,
                    "timeline":
                    timeline_results,
                    "conversations":
                    conversation_results,
                },
            },
            status=status.HTTP_200_OK,
        )