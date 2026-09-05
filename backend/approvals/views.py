from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from inbox.models import OrganizationUser
from .models import ApprovalItem
from .serializers import ApprovalItemSerializer
from .tasks import send_approval_assignment_notification
from actions.models import ActionItem
from notifications.services import create_notification
from timeline.services import create_timeline_event

from platform_core.api.tenant import (
    get_user_organization_or_404,
)


def apply_decision(item, new_status, user, notes=""):
    item.status = new_status
    item.decision_notes = notes
    item.decision_by = user
    item.decision_at = timezone.now()
    item.save(update_fields=["status", "decision_notes", "decision_by", "decision_at"])


class ApprovalListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization = (
            get_user_organization_or_404(
                request
            )
        )

        approvals = (
            ApprovalItem.objects
            .filter(
                user=request.user,
                organization=organization,
            )
            .order_by(
                "-created_at"
            )
        )

        serializer = ApprovalItemSerializer(
            approvals,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class PendingApprovalListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization = (
            get_user_organization_or_404(
                request
            )
        )

        approvals = (
            ApprovalItem.objects
            .filter(
                user=request.user,
                organization=organization,
                status="pending",
            )
            .order_by(
                "due_date",
                "-created_at",
            )
        )

        serializer = ApprovalItemSerializer(
            approvals,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class TeamMemberListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            organization = request.user.organization_membership.organization
        except Exception:
            return Response([], status=status.HTTP_200_OK)

        members = (
            OrganizationUser.objects
            .filter(organization=organization)
            .select_related("user")
            .order_by("user__email")
        )

        data = [
            {
                "id": member.user.id,
                "email": member.user.email,
                "role": member.role,
            }
            for member in members
        ]

        return Response(data, status=status.HTTP_200_OK)


class AssignApprovalAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, approval_id):
        organization = (
            get_user_organization_or_404(
                request
            )
        )

        try:
            item = ApprovalItem.objects.get(
                id=approval_id,
                user=request.user,
                organization=organization,
            )
        except ApprovalItem.DoesNotExist:
            return Response(
                {"error": "Approval not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        assigned_to_id = request.data.get("assigned_to")

        try:
            organization = request.user.organization_membership.organization
        except Exception:
            return Response(
                {"error": "Organization not found"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not assigned_to_id:
            item.assigned_to = None
            item.save(update_fields=["assigned_to"])

            return Response(
                {
                    "status": "unassigned",
                    "assigned_to": None,
                    "assigned_to_email": None,
                },
                status=status.HTTP_200_OK
            )

        member = (
            OrganizationUser.objects
            .select_related("user")
            .filter(
                organization=organization,
                user__id=assigned_to_id
            )
            .first()
        )

        if not member:
            return Response(
                {"error": "Assignee must belong to your organization"},
                status=status.HTTP_400_BAD_REQUEST
            )

        item.assigned_to = member.user
        item.save(update_fields=["assigned_to"])

        if item.conversation:

            create_timeline_event(
                conversation=item.conversation,
                event_type="approval_created",
                title="Approval assigned",
                details={
                    "approval_id": item.id,
                    "approval_title": item.title,
                    "assigned_to": member.user.email,
                },
            )

        send_approval_assignment_notification.delay(
            item.id,
            item.assigned_to.id,
            request.user.id,
        )

        return Response(
            {
                "status": "assigned",
                "notification": "sent",
                "assigned_to": item.assigned_to.id,
                "assigned_to_email": item.assigned_to.email,
            },
            status=status.HTTP_200_OK
        )


class ApproveItemAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, approval_id):

        organization = (
            get_user_organization_or_404(
                request
            )
        )

        try:
            item = ApprovalItem.objects.get(
                id=approval_id,
                user=request.user,
                organization=organization,
            )

        except ApprovalItem.DoesNotExist:

            return Response(
                {
                    "error": "Approval not found"
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        notes = request.data.get(
            "decision_notes",
            "",
        )

        apply_decision(
            item,
            "approved",
            request.user,
            notes,
        )

        if item.conversation:

            create_timeline_event(
                conversation=item.conversation,
                event_type="approval_approved",
                title="Approval approved",
                details={
                    "approval_id": item.id,
                    "approval_title": item.title,
                    "approved_by": request.user.email,
                },
            )

        action_created = False

        if not item.action_created:

            ActionItem.objects.create(

                user=item.user,

                organization=item.organization,

                message=item.message,

                title=item.title,

                description=item.description,

                owner=item.assigned_to,

                due_date=item.due_date,

                priority=80,

                confidence_score=item.confidence_score,

                source_approval=item,

            )

            item.action_created = True

            item.save(
                update_fields=[
                    "action_created"
                ]
            )

            action_created = True

            create_notification(

                user=item.user,

                type="new_email",

                title="Action Created",

                message=(
                    f'Action "{item.title}" '
                    f'was automatically created '
                    f'after approval.'
                ),
            )

        return Response(
            {
                "status": "approved",
                "action_created": action_created,
            },
            status=status.HTTP_200_OK,
        )


class RejectItemAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, approval_id):
        organization = (
            get_user_organization_or_404(
                request
            )
        )

        try:
            item = ApprovalItem.objects.get(id=approval_id, user=request.user, organization=organization)
        except ApprovalItem.DoesNotExist:
            return Response(
                {"error": "Approval not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        notes = request.data.get("decision_notes", "")
        apply_decision(item, "rejected", request.user, notes)

        if item.conversation:

            create_timeline_event(
                conversation=item.conversation,
                event_type="approval_rejected",
                title="Approval rejected",
                details={
                    "approval_id": item.id,
                    "approval_title": item.title,
                    "rejected_by": request.user.email,
                },
            )

        return Response({"status": "rejected"}, status=status.HTTP_200_OK)


class NeedsInfoItemAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, approval_id):
        organization = (
            get_user_organization_or_404(
                request
            )
        )

        try:
            item = ApprovalItem.objects.get(id=approval_id, user=request.user, organization=organization)
        except ApprovalItem.DoesNotExist:
            return Response(
                {"error": "Approval not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        notes = request.data.get("decision_notes", "")
        apply_decision(item, "needs_info", request.user, notes)
        if item.conversation:

            create_timeline_event(
                conversation=item.conversation,
                event_type="approval_created",
                title="More information requested",
                details={
                    "approval_id": item.id,
                    "approval_title": item.title,
                    "requested_by": request.user.email,
                },
            )

        return Response({"status": "needs_info"}, status=status.HTTP_200_OK)


class IgnoreApprovalAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, approval_id):
        organization = (
            get_user_organization_or_404(
                request
            )
        )

        try:
            item = ApprovalItem.objects.get(id=approval_id, user=request.user, organization=organization)
        except ApprovalItem.DoesNotExist:
            return Response(
                {"error": "Approval not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        notes = request.data.get("decision_notes", "")
        apply_decision(item, "ignored", request.user, notes)

        return Response({"status": "ignored"}, status=status.HTTP_200_OK)


class ReopenApprovalAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, approval_id):
        organization = (
            get_user_organization_or_404(
                request
            )
        )

        try:
            item = ApprovalItem.objects.get(id=approval_id, user=request.user, organization=organization)
        except ApprovalItem.DoesNotExist:
            return Response(
                {"error": "Approval not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        notes = request.data.get("decision_notes", "")
        apply_decision(item, "pending", request.user, notes)

        if item.conversation:

            create_timeline_event(
                conversation=item.conversation,
                event_type="approval_created",
                title="Approval reopened",
                details={
                    "approval_id": item.id,
                    "approval_title": item.title,
                    "reopened_by": request.user.email,
                },
            )

        return Response({"status": "reopened"}, status=status.HTTP_200_OK)