from dataclasses import dataclass
from typing import Literal


Decision = Literal[
    "auto_create",
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

    This function performs no database writes.
    """

    confidence_score = max(
        0,
        min(
            int(confidence_score),
            100,
        ),
    )

    if confidence_score >= auto_create_threshold:
        return ActionExtractionDecision(
            decision="auto_create",
            confidence_score=confidence_score,
            reason=(
                "AI confidence meets automatic "
                "creation threshold."
            ),
        )

    if confidence_score >= review_threshold:
        return ActionExtractionDecision(
            decision="review",
            confidence_score=confidence_score,
            reason=(
                "AI confidence requires human review."
            ),
        )

    return ActionExtractionDecision(
        decision="ignore",
        confidence_score=confidence_score,
        reason=(
            "AI confidence is below review threshold."
        ),
    )
