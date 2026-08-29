from dataclasses import (
    asdict,
    dataclass,
)
from typing import Optional

from approvals.models import (
    ApprovalItem,
)

from knowledge.services.intelligence_evidence_builders import (
    build_approval_evidence,
)


@dataclass(frozen=True)
class DecisionItem:
    """
    One currently final Approval decision.

    This is a read-only projection.

    ApprovalItem remains the authoritative business state.
    """

    decision_id: str
    approval_id: int

    organization_id: int

    conversation_id: Optional[int]
    source_message_id: Optional[int]

    title: str
    description: str

    outcome: str

    decision_notes: str

    decision_by_id: Optional[int]
    decision_by_email: Optional[str]
    decision_at: object

    requested_by: Optional[str]

    assigned_to_id: Optional[int]
    assigned_to_email: Optional[str]

    source_type: str

    created_at: object
    updated_at: object

    request_evidence: dict

    open_url: Optional[str]

    def to_dict(self):
        return asdict(
            self
        )


class DecisionsService:
    """
    Read-only current Decisions register.

    Only final Approval outcomes are decisions:

        approved
        rejected

    Pending, needs-info, ignored and reopened approvals are
    intentionally excluded.
    """

    OUTCOME_APPROVED = "approved"
    OUTCOME_REJECTED = "rejected"

    FINAL_OUTCOMES = {
        OUTCOME_APPROVED,
        OUTCOME_REJECTED,
    }

    @classmethod
    def build(
        cls,
        *,
        organization,
    ):
        approvals = (
            ApprovalItem.objects
            .filter(
                organization=organization,
                status__in=(
                    cls.FINAL_OUTCOMES
                ),
            )
            .select_related(
                "message",
                "conversation",
                "decision_by",
                "assigned_to",
            )
        )

        items = []

        for approval in approvals:
            evidence = (
                build_approval_evidence(
                    approval
                )
                .to_dict()
            )

            items.append(
                DecisionItem(
                    decision_id=(
                        "approval_decision:"
                        f"{approval.id}"
                    ),

                    approval_id=(
                        approval.id
                    ),

                    organization_id=(
                        approval.organization_id
                    ),

                    conversation_id=(
                        approval.message.conversation_id
                        if approval.message_id
                        else approval.conversation_id
                    ),

                    source_message_id=(
                        approval.message_id
                    ),

                    title=(
                        approval.title
                    ),

                    description=(
                        approval.description
                        or ""
                    ),

                    outcome=(
                        approval.status
                    ),

                    decision_notes=(
                        approval.decision_notes
                        or ""
                    ),

                    decision_by_id=(
                        approval.decision_by_id
                    ),

                    decision_by_email=(
                        approval.decision_by.email
                        if approval.decision_by
                        else None
                    ),

                    decision_at=(
                        approval.decision_at
                    ),

                    requested_by=(
                        approval.requested_by
                    ),

                    assigned_to_id=(
                        approval.assigned_to_id
                    ),

                    assigned_to_email=(
                        approval.assigned_to.email
                        if approval.assigned_to
                        else None
                    ),

                    source_type=(
                        approval.source_type
                    ),

                    created_at=(
                        approval.created_at
                    ),

                    updated_at=(
                        approval.updated_at
                    ),

                    request_evidence=(
                        evidence
                    ),

                    open_url=(
                        cls._open_url(
                            (
                                approval.message.conversation_id
                                if approval.message_id
                                else approval.conversation_id
                            )
                        )
                    ),
                )
            )

        return sorted(
            items,
            key=cls._sort_key,
            reverse=True,
        )

    @classmethod
    def summary(
        cls,
        items,
    ):
        return {
            "total": len(
                items
            ),

            "approved": sum(
                1
                for item in items
                if (
                    item.outcome
                    == cls.OUTCOME_APPROVED
                )
            ),

            "rejected": sum(
                1
                for item in items
                if (
                    item.outcome
                    == cls.OUTCOME_REJECTED
                )
            ),

            "with_notes": sum(
                1
                for item in items
                if (
                    item.decision_notes
                    .strip()
                )
            ),

            "exact_request_evidence": sum(
                1
                for item in items
                if (
                    item.request_evidence
                    .get(
                        "evidence_quality"
                    )
                    == "exact"
                )
            ),
        }

    @classmethod
    def build_payload(
        cls,
        *,
        organization,
    ):
        items = cls.build(
            organization=organization
        )

        return {
            "organization_id":
                organization.id,

            "summary":
                cls.summary(
                    items
                ),

            "items": [
                item.to_dict()
                for item in items
            ],
        }

    @staticmethod
    def _open_url(
        conversation_id,
    ):
        if conversation_id is None:
            return None

        return (
            "/inbox?conversation="
            f"{conversation_id}"
        )

    @staticmethod
    def _sort_key(
        item,
    ):
        effective_at = (
            item.decision_at
            or item.updated_at
            or item.created_at
        )

        return (
            effective_at.timestamp(),
            item.approval_id,
        )
