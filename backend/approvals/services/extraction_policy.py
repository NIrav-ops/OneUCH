from dataclasses import dataclass
from typing import Literal


Decision = Literal[
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

    AI Approval creation is review-only.

    The auto_create_threshold argument is retained for
    backward-compatible callers and configuration, but
    automatic AI Approval creation is intentionally disabled.

    This function performs no database writes.
    """

    # Retained only for backward-compatible callers.
    _ = auto_create_threshold

    confidence_score = max(
        0,
        min(
            int(confidence_score),
            100,
        ),
    )

    if confidence_score >= review_threshold:
        return ApprovalExtractionDecision(
            decision="review",
            confidence_score=confidence_score,
            reason=(
                "AI Approval candidates require human "
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
