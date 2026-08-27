from dataclasses import dataclass
from typing import Literal


Decision = Literal[
    "auto_create",
    "review",
    "ignore",
]


@dataclass(frozen=True)
class ApprovalExtractionDecision:
    decision: Decision
    confidence_score: int
    reason: str


def decide_ai_approval(
    *,
    confidence_score: int,
    auto_create_threshold: int = 95,
    review_threshold: int = 85,
) -> ApprovalExtractionDecision:
    """
    Decide how One UCH should treat one validated
    semantic Approval candidate.

    This function performs no database writes.
    """

    confidence_score = max(
        0,
        min(
            int(confidence_score),
            100,
        ),
    )

    if (
        review_threshold
        > auto_create_threshold
    ):
        review_threshold = (
            auto_create_threshold
        )

    if (
        confidence_score
        >= auto_create_threshold
    ):
        return ApprovalExtractionDecision(
            decision="auto_create",
            confidence_score=confidence_score,
            reason=(
                "AI confidence meets automatic "
                "Approval creation threshold."
            ),
        )

    if (
        confidence_score
        >= review_threshold
    ):
        return ApprovalExtractionDecision(
            decision="review",
            confidence_score=confidence_score,
            reason=(
                "AI confidence requires human "
                "review before Approval creation."
            ),
        )

    return ApprovalExtractionDecision(
        decision="ignore",
        confidence_score=confidence_score,
        reason=(
            "AI confidence is below the Approval "
            "review threshold."
        ),
    )
