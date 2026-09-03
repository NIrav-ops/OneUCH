from dataclasses import dataclass
from typing import Literal


Decision = Literal[
    "review",
    "ignore",
]


@dataclass(frozen=True)
class ActionExtractionDecision:
    decision: Decision
    confidence_score: int
    reason: str


def decide_ai_action(
    *,
    confidence_score: int,
    auto_create_threshold: int = 90,
    review_threshold: int = 75,
) -> ActionExtractionDecision:
    """
    Decide how One UCH should treat one validated
    AI Action candidate.

    AI Action creation is review-only.

    The auto_create_threshold argument is retained for
    backward-compatible callers and configuration, but
    automatic AI Action creation is intentionally disabled.

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
        return ActionExtractionDecision(
            decision="review",
            confidence_score=confidence_score,
            reason=(
                "AI Action candidates require human "
                "review before Action creation."
            ),
        )

    return ActionExtractionDecision(
        decision="ignore",
        confidence_score=confidence_score,
        reason=(
            "AI confidence is below review threshold."
        ),
    )
