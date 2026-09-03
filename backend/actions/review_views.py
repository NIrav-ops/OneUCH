from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from actions.models import (
    ActionItem,
    AIActionCandidate,
)
from actions.tasks import _create_action


def _organization_for(user):
    try:
        return (
            user
            .organization_membership
            .organization
        )
    except Exception:
        return None


def _occurrence_payload(
    occurrence,
):
    message = occurrence.message
    conversation_id = (
        message.conversation_id
    )

    return {
        "message":
            occurrence.message_id,
        "conversation":
            conversation_id,
        "subject":
            message.subject
            or "No Subject",
        "source_domain":
            occurrence.source_domain,
        "extraction_method":
            occurrence.extraction_method,
        "observed_at":
            occurrence.observed_at,
        "open_url": (
            f"/inbox?conversation={conversation_id}"
            if conversation_id
            else "/inbox"
        ),
    }


def _candidate_payload(candidate):
    message = candidate.message
    conversation_id = message.conversation_id

    history = [
        _occurrence_payload(
            occurrence
        )
        for occurrence in (
            candidate
            .occurrences
            .select_related(
                "message",
                "message__conversation",
            )
            .all()[:20]
        )
    ]

    return {
        "id": candidate.id,
        "message": candidate.message_id,
        "conversation": conversation_id,
        "subject": message.subject or "No Subject",
        "title": candidate.title,
        "description": candidate.description,
        "owner_reference": candidate.owner_reference,
        "due_date": candidate.due_date,
        "priority": candidate.priority,
        "confidence_score": candidate.confidence_score,
        "evidence": candidate.evidence,
        "reason": candidate.reason,
        "provider": candidate.provider,
        "model": candidate.model,
        "extraction_method":
            candidate.extraction_method,
        "source_domain":
            candidate.source_domain,
        "occurrence_count":
            candidate.occurrence_count,
        "last_seen_at":
            candidate.last_seen_at,
        "history":
            history,
        "status": candidate.status,
        "created_at": candidate.created_at,
        "updated_at": candidate.updated_at,
        "open_url": (
            f"/inbox?conversation={conversation_id}"
            if conversation_id
            else "/inbox"
        ),
    }


def _candidate_source_type(
    candidate,
):
    if (
        candidate.extraction_method
        == "deterministic"
    ):
        return "email"

    return "ai"


def _candidate_processing_mode(
    candidate,
):
    if (
        candidate.extraction_method
        == "deterministic"
    ):
        return "deterministic"

    return "unknown"

def _source_tenant_is_valid(candidate):
    return (
        candidate.user_id is not None
        and candidate.message.user_id
        == candidate.user_id
        and candidate.message.organization_id
        == candidate.organization_id
    )


class AIActionCandidateListAPIView(APIView):
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
            AIActionCandidate.objects
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


class PromoteAIActionCandidateAPIView(APIView):
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
            AIActionCandidate.objects
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
                        "Action review candidate not found"
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

        promoted_source_type = (
            _candidate_source_type(
                candidate
            )
        )

        existing = (
            ActionItem.objects
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
                or existing.source_type != promoted_source_type
            ):
                return Response(
                    {
                        "error":
                            "Promoted candidate has no governed Action"
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            return Response(
                {
                    "status": "promoted",
                    "created": False,
                    "action_id": existing.id,
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
                        "A governed Action already exists for this candidate"
                },
                status=status.HTTP_409_CONFLICT,
            )

        action, created = _create_action(
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
                    _candidate_processing_mode(
                        candidate
                    ),
                "provider": candidate.provider,
                "model": candidate.model,
            },
            source_type=(
                promoted_source_type
            ),
        )

        if not created:
            raise RuntimeError(
                "Expected promoted Action creation."
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
                "action_id": action.id,
            },
            status=status.HTTP_200_OK,
        )


class RejectAIActionCandidateAPIView(APIView):
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
            AIActionCandidate.objects
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
                        "Action review candidate not found"
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
