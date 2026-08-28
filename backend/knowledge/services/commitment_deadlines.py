from dataclasses import dataclass

from django.utils import timezone
from django.utils.dateparse import (
    parse_datetime,
)

from actions.models import (
    ActionItem,
    ExpectedResponseItem,
)

from knowledge.models import (
    KnowledgeEvidence,
)

from knowledge.services.intelligence_evidence_builders import (
    intelligence_evidence_title,
)


@dataclass(frozen=True)
class CommitmentDeadlineSummary:
    """
    Read-only normalized commitment deadline history.

    Current state always comes from the domain object.
    Historical values come from governed evidence metadata.
    """

    original_due_at: object
    current_due_at: object
    change_count: int
    history: tuple


def _parse_due_at(
    value,
):
    if not value:
        return None

    parsed = parse_datetime(
        value
    )

    if parsed is None:
        return None

    if timezone.is_naive(
        parsed
    ):
        parsed = timezone.make_aware(
            parsed,
            timezone.get_current_timezone(),
        )

    return parsed


def _identity(
    instance,
):
    if isinstance(
        instance,
        ActionItem,
    ):
        return (
            "action",
            instance.due_date,
        )

    if isinstance(
        instance,
        ExpectedResponseItem,
    ):
        return (
            "expected_response",
            instance.response_due_at,
        )

    raise ValueError(
        "Unsupported commitment object."
    )


def build_commitment_deadline_summary(
    instance,
):
    """
    Reconstruct original/current deadline semantics without
    duplicating ActionItem or ExpectedResponseItem state.
    """

    object_type, current_due_at = (
        _identity(
            instance
        )
    )

    title = (
        intelligence_evidence_title(
            object_type,
            instance.id,
        )
    )

    rows = (
        KnowledgeEvidence.objects
        .filter(
            organization_id=(
                instance.organization_id
            ),
            title=title,
            is_archived=False,
        )
        .order_by(
            "-updated_at",
            "-created_at",
            "-id",
        )
    )

    history = []

    # Newest evidence carries forward the complete history.
    for row in rows:
        metadata = (
            row.metadata
            if isinstance(
                row.metadata,
                dict,
            )
            else {}
        )

        candidate = (
            metadata.get(
                "deadline_history"
            )
        )

        if isinstance(
            candidate,
            list,
        ):
            history = [
                dict(item)
                for item
                in candidate
                if isinstance(
                    item,
                    dict,
                )
            ]

            if history:
                break

    if not history:
        return CommitmentDeadlineSummary(
            original_due_at=(
                current_due_at
            ),
            current_due_at=(
                current_due_at
            ),
            change_count=0,
            history=(),
        )

    original_due_at = (
        _parse_due_at(
            history[0].get(
                "due_at"
            )
        )
    )

    return CommitmentDeadlineSummary(
        original_due_at=(
            original_due_at
        ),
        current_due_at=(
            current_due_at
        ),
        change_count=max(
            len(history) - 1,
            0,
        ),
        history=tuple(
            history
        ),
    )
