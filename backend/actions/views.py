from datetime import datetime
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from inbox.models import OrganizationUser
from .models import ActionItem, FollowUpItem
from .serializers import ActionItemSerializer, FollowUpItemSerializer
from notifications.services import create_notification
from timeline.services import create_timeline_event
from django.contrib.auth import get_user_model

from knowledge.services.intelligence_evidence_persistence import (
    persist_intelligence_evidence,
)

from platform_core.api.tenant import (
    get_user_organization_or_404,
)

User = get_user_model()

def get_user_organization(user):
    try:
        return user.organization_membership.organization
    except Exception:
        return None


def parse_due_date(value):
    """
    Accepts:
    - ISO datetime string from datetime-local input
    - ISO datetime string with timezone
    - date string YYYY-MM-DD
    """
    if not value:
        return None

    dt = parse_datetime(value)
    if dt is not None:
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        return dt

    d = parse_date(value)
    if d is not None:
        dt = datetime.combine(d, datetime.min.time())
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
        return dt

    return None


class ActionListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization = (
            get_user_organization_or_404(
                request
            )
        )

        actions = (
            ActionItem.objects.filter(
                user=request.user,
                organization=organization,
            )
            .select_related(
                "owner",
                "message",
                "source_approval",
            )
            .order_by(
                "-priority",
                "-created_at",
            )
        )

        serializer = ActionItemSerializer(
            actions,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class FollowUpListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization = (
            get_user_organization_or_404(
                request
            )
        )

        followups = (
            FollowUpItem.objects.filter(
                user=request.user,
                organization=organization,
                status="pending",
            )
            .select_related("conversation", "last_message")
            .order_by("followup_due_at", "-created_at")
        )
        serializer = FollowUpItemSerializer(followups, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TeamMemberListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization = get_user_organization(request.user)
        if not organization:
            return Response([], status=status.HTTP_200_OK)

        members = (
            OrganizationUser.objects.filter(organization=organization)
            .select_related("user")
            .order_by("user__email")
        )

        data = [
            {
                "id": member.user.id,
                "email": member.user.email,
                "role": getattr(member, "role", "member"),
            }
            for member in members
        ]
        return Response(data, status=status.HTTP_200_OK)


class UpdateActionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, action_id):
        organization = (
            get_user_organization_or_404(
                request
            )
        )

        try:
            action = ActionItem.objects.get(id=action_id, user=request.user, organization=organization)
        except ActionItem.DoesNotExist:
            return Response(
                {"error": "Action not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        assigned_to_id = request.data.get("assigned_to", "")
        due_date_value = request.data.get("due_date", "")

        update_fields = []

        organization = get_user_organization(request.user)

        # OWNER / ASSIGNEE
        if assigned_to_id == "":
            action.owner = None
            update_fields.append("owner")
        elif assigned_to_id is not None:
            if not organization:
                return Response(
                    {"error": "Organization not found"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            member = (
                OrganizationUser.objects.select_related("user")
                .filter(
                    organization=organization,
                    user__id=assigned_to_id,
                )
                .first()
            )

            if not member:
                return Response(
                    {"error": "Assignee must belong to your organization"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            action.owner = member.user
            update_fields.append("owner")
            if action.message and action.message.conversation:

                create_timeline_event(
                    conversation=action.message.conversation,
                    event_type="action_created",
                    title="Action reassigned",
                    details={
                        "action_id": action.id,
                        "action_title": action.title,
                        "new_owner": member.user.email,
                    },
                )

        # DUE DATE
        parsed_due_date = parse_due_date(due_date_value)
        if due_date_value == "":
            action.due_date = None
            update_fields.append("due_date")
        elif parsed_due_date is not None:
            action.due_date = parsed_due_date
            update_fields.append("due_date")

        # OPTIONAL PRIORITY
        if "priority" in request.data:
            try:
                action.priority = int(request.data.get("priority") or 0)
                update_fields.append("priority")
            except (TypeError, ValueError):
                pass

        if update_fields:
            action.save(update_fields=update_fields)

        if (
            "due_date" in update_fields
            and action.message_id
        ):
            persist_intelligence_evidence(
                action,
                deadline_source=(
                    "manual_update"
                ),
            )

        return Response(
            {
                "status": "updated",
                "owner": action.owner.id if action.owner else None,
                "owner_email": action.owner.email if action.owner else None,
                "due_date": action.due_date,
                "priority": action.priority,
            },
            status=status.HTTP_200_OK,
        )


class CompleteActionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, action_id):
        organization = (
            get_user_organization_or_404(
                request
            )
        )

        try:
            action = ActionItem.objects.get(id=action_id, user=request.user, organization=organization)
        except ActionItem.DoesNotExist:
            return Response(
                {"error": "Action not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        was_completed = (
            action.status == "completed"
        )

        if not was_completed:
            action.status = "completed"
            action.completed_at = (
                timezone.now()
            )

            action.save(
                update_fields=[
                    "status",
                    "completed_at",
                ]
            )

            if (
                action.message
                and action.message.conversation
            ):
                create_timeline_event(
                    conversation=(
                        action.message
                        .conversation
                    ),
                    event_type=(
                        "action_completed"
                    ),
                    title=(
                        "Action completed"
                    ),
                    details={
                        "action_id":
                            action.id,

                        "action_title":
                            action.title,

                        "completed_by":
                            request.user.email,

                        "completed_by_user_id":
                            request.user.id,
                    },
                    event_at=(
                        action.completed_at
                    ),
                )

        return Response({"status": "completed"}, status=status.HTTP_200_OK)

class StartActionAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, action_id):

        organization = (
            get_user_organization_or_404(
                request
            )
        )

        try:

            action = ActionItem.objects.get(
                id=action_id,
                user=request.user,
                organization=organization,
            )

        except ActionItem.DoesNotExist:

            return Response(
                {
                    "error":"Not found"
                },
                status=404,
            )

        action.status="in_progress"
        action.completed_at=None

        action.save(
            update_fields=[
                "status",
                "completed_at",
            ]
        )

        create_notification(

            organization=action.organization,

            user=action.user,

            type="new_email",

            title="Action Started",

            message=(
                f'Action "{action.title}" '
                f'has started.'
            ),
        )

        return Response(
            {
                "status":"in_progress"
            }
        )


class IgnoreActionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, action_id):
        organization = (
            get_user_organization_or_404(
                request
            )
        )

        try:
            action = ActionItem.objects.get(id=action_id, user=request.user, organization=organization)
        except ActionItem.DoesNotExist:
            return Response(
                {"error": "Action not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        action.status = "ignored"
        action.completed_at = None

        action.save(
            update_fields=[
                "status",
                "completed_at",
            ]
        )

        return Response({"status": "ignored"}, status=status.HTTP_200_OK)


class ReopenActionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, action_id):
        organization = (
            get_user_organization_or_404(
                request
            )
        )

        try:
            action = ActionItem.objects.get(id=action_id, user=request.user, organization=organization)
        except ActionItem.DoesNotExist:
            return Response(
                {"error": "Action not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        action.status = "open"
        action.completed_at = None

        action.save(
            update_fields=[
                "status",
                "completed_at",
            ]
        )

        return Response({"status": "reopened"}, status=status.HTTP_200_OK)


class SnoozeFollowUpAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, followup_id):
        organization = (
            get_user_organization_or_404(
                request
            )
        )

        try:
            followup = FollowUpItem.objects.get(id=followup_id, user=request.user, organization=organization)
        except FollowUpItem.DoesNotExist:
            return Response(
                {"error": "Follow-up not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        days = request.data.get("days", 1)

        try:
            days = int(days)
        except (TypeError, ValueError):
            days = 1

        followup.followup_due_at = timezone.now() + timezone.timedelta(days=days)
        followup.status = "pending"
        followup.save(update_fields=["followup_due_at", "status"])

        return Response(
            {
                "status": "snoozed",
                "followup_due_at": followup.followup_due_at,
            },
            status=status.HTTP_200_OK,
        )
    
class UpdateActionStatusAPIView(APIView):

    permission_classes = [IsAuthenticated]

    VALID = [
        "open",
        "in_progress",
        "waiting",
        "blocked",
        "completed",
        "cancelled",
        "ignored",
    ]

    def post(self, request, action_id):

        organization = (
            get_user_organization_or_404(
                request
            )
        )

        try:

            action = ActionItem.objects.get(
                id=action_id,
                user=request.user,
                organization=organization,
            )

        except ActionItem.DoesNotExist:

            return Response(
                {
                    "error":"Not found"
                },
                status=404,
            )

        new_status=request.data.get("status")

        if new_status not in self.VALID:

            return Response(
                {
                    "error":"Invalid status"
                },
                status=400,
            )

        previous_status = (
            action.status
        )

        action.status=new_status

        if new_status=="completed":
            if previous_status != "completed":
                action.completed_at=(
                    timezone.now()
                )

        else:
            action.completed_at=None

        action.save()

        if (
            new_status == "completed"
            and previous_status
            != "completed"
            and action.message
            and action.message.conversation
        ):
            create_timeline_event(
                conversation=(
                    action.message
                    .conversation
                ),
                event_type=(
                    "action_completed"
                ),
                title="Action completed",
                details={
                    "action_id":
                        action.id,

                    "action_title":
                        action.title,

                    "completed_by":
                        request.user.email,

                    "completed_by_user_id":
                        request.user.id,
                },
                event_at=(
                    action.completed_at
                ),
            )

        create_notification(

            organization=action.organization,

            user=action.user,

            type="new_email",

            title="Action Updated",

            message=(
                f'{action.title} '
                f'is now '
                f'{new_status}.'
            ),
        )

        return Response(
            {
                "status":new_status
            }
        )

class AssignActionAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, action_id):

        organization = (
            get_user_organization_or_404(
                request
            )
        )

        try:
            action = ActionItem.objects.get(
                id=action_id,
                user=request.user,
                organization=organization,
            )

        except ActionItem.DoesNotExist:

            return Response(
                {
                    "error": "Action not found"
                },
                status=404,
            )

        owner_id = request.data.get("owner")

        if not owner_id:

            action.owner = None

            action.save(
                update_fields=[
                    "owner"
                ]
            )

            return Response(
                {
                    "status": "unassigned"
                }
            )

        membership = (
            OrganizationUser.objects
            .select_related(
                "user"
            )
            .filter(
                organization=organization,
                user__id=owner_id,
            )
            .first()
        )

        if membership is None:

            return Response(
                {
                    "error": (
                        "Owner must belong "
                        "to your organization"
                    )
                },
                status=400,
            )

        owner = membership.user

        action.owner = owner

        action.save(
            update_fields=[
                "owner"
            ]
        )

        create_notification(

            organization=action.organization,

            user=owner,

            type="new_email",

            title="Action Assigned",

            message=(
                f'You have been assigned '
                f'"{action.title}".'
            ),
        )

        return Response(
            {
                "status": "assigned",
                "owner": owner.email,
            }
        )