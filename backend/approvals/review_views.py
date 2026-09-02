from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from approvals.models import (
    ApprovalItem,
    AIApprovalCandidate,
)
from approvals.tasks import _create_approval


def _organization_for(user):
    try:
        return (
            user
            .organization_membership
            .organization
        )
    except Exception:
        return None


def _candidate_payload(candidate):
    message = candidate.message
    conversation_id = message.conversation_id

    return {
        "id": candidate.id,
        "message": candidate.message_id,
        "conversation": conversation_id,
        "subject": message.subject or "No Subject",
        "title": candidate.title,
        "description": candidate.description,
        "approver_reference":
            candidate.approver_reference,
        "due_date": candidate.due_date,
        "priority": candidate.priority,
        "confidence_score": candidate.confidence_score,
        "evidence": candidate.evidence,
        "reason": candidate.reason,
        "provider": candidate.provider,
        "model": candidate.model,
        "status": candidate.status,
        "created_at": candidate.created_at,
        "updated_at": candidate.updated_at,
        "open_url": (
            f"/inbox?conversation={conversation_id}"
            if conversation_id
            else "/inbox"
        ),
    }


def _source_tenant_is_valid(candidate):
    return (
        candidate.user_id is not None
        and candidate.message.user_id
        == candidate.user_id
        and candidate.message.organization_id
        == candidate.organization_id
    )


class AIApprovalCandidateListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization = _organization_for(
            request.user
        )

        if organization is None:
            return Response(
                [],
                status=status.HTTP_200_OK,
            )

        candidates = (
            AIApprovalCandidate.objects
            .filter(
                user=request.user,
                organization=organization,
                status="pending_review",
            )
            .select_related(
                "message",
                "message__conversation",
            )
            .order_by(
                "-confidence_score",
                "-created_at",
            )
        )

        return Response(
            [
                _candidate_payload(candidate)
                for candidate in candidates
            ],
            status=status.HTTP_200_OK,
        )


class PromoteAIApprovalCandidateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(
        self,
        request,
        candidate_id,
    ):
        organization = _organization_for(
            request.user
        )

        if organization is None:
            return Response(
                {
                    "error":
                        "Organization not found"
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        candidate = (
            AIApprovalCandidate.objects
            .select_for_update()
            .select_related(
                "message",
                "message__conversation",
            )
            .filter(
                id=candidate_id,
                user=request.user,
                organization=organization,
            )
            .first()
        )

        if candidate is None:
            return Response(
                {
                    "error":
                        "AI Approval candidate not found"
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if not _source_tenant_is_valid(
            candidate
        ):
            return Response(
                {
                    "error":
                        "Candidate source tenant mismatch"
                },
                status=status.HTTP_409_CONFLICT,
            )

        existing = (
            ApprovalItem.objects
            .filter(
                user=request.user,
                organization=organization,
                message=candidate.message,
                title=candidate.title,
            )
            .first()
        )

        if candidate.status == "promoted":
            if (
                existing is None
                or existing.source_type != "ai"
            ):
                return Response(
                    {
                        "error":
                            "Promoted candidate has no governed AI Approval"
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            return Response(
                {
                    "status": "promoted",
                    "created": False,
                    "approval_id": existing.id,
                },
                status=status.HTTP_200_OK,
            )

        if candidate.status == "rejected":
            return Response(
                {
                    "error":
                        "Rejected candidate cannot be promoted"
                },
                status=status.HTTP_409_CONFLICT,
            )

        if candidate.status != "pending_review":
            return Response(
                {
                    "error":
                        "Candidate is not pending review"
                },
                status=status.HTTP_409_CONFLICT,
            )

        if existing is not None:
            return Response(
                {
                    "error":
                        "A governed Approval already exists for this candidate"
                },
                status=status.HTTP_409_CONFLICT,
            )

        approval, created = _create_approval(
            msg=candidate.message,
            item={
                "title": candidate.title,
                "description": candidate.description,
                "priority": candidate.priority,
                "due_date": candidate.due_date,
                "confidence_score":
                    candidate.confidence_score,
                "evidence": candidate.evidence,
                "processing_mode":
                    "unknown",
                "provider": candidate.provider,
                "model": candidate.model,
            },
            source_type="ai",
        )

        if not created:
            raise RuntimeError(
                "Expected promoted Approval creation."
            )

        candidate.status = "promoted"
        candidate.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return Response(
            {
                "status": "promoted",
                "created": True,
                "approval_id": approval.id,
            },
            status=status.HTTP_200_OK,
        )


class RejectAIApprovalCandidateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(
        self,
        request,
        candidate_id,
    ):
        organization = _organization_for(
            request.user
        )

        if organization is None:
            return Response(
                {
                    "error":
                        "Organization not found"
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        candidate = (
            AIApprovalCandidate.objects
            .select_for_update()
            .select_related("message")
            .filter(
                id=candidate_id,
                user=request.user,
                organization=organization,
            )
            .first()
        )

        if candidate is None:
            return Response(
                {
                    "error":
                        "AI Approval candidate not found"
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if not _source_tenant_is_valid(
            candidate
        ):
            return Response(
                {
                    "error":
                        "Candidate source tenant mismatch"
                },
                status=status.HTTP_409_CONFLICT,
            )

        if candidate.status == "promoted":
            return Response(
                {
                    "error":
                        "Promoted candidate cannot be rejected"
                },
                status=status.HTTP_409_CONFLICT,
            )

        changed = (
            candidate.status
            != "rejected"
        )

        if changed:
            candidate.status = "rejected"
            candidate.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

        return Response(
            {
                "status": "rejected",
                "changed": changed,
            },
            status=status.HTTP_200_OK,
        )
