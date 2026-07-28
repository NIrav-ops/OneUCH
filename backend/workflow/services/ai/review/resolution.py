"""
Enterprise AI Human Review Resolution Service.

Validates and resolves human decisions made against
pending AI governance review requests.

This module intentionally contains no:
- database persistence
- workflow resume logic
- executor logic
- provider calls
- external side effects

Its responsibility is deterministic review resolution only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .contracts import (
    AIHumanReviewDecision,
    AIHumanReviewRequest,
)


class AIHumanReviewResolutionError(Exception):
    """
    Raised when a human-review decision cannot safely
    resolve the supplied review request.
    """


@dataclass(frozen=True)
class AIHumanReviewResolution:
    """
    Immutable result of resolving a human review.

    `can_continue` means the reviewed AI output may proceed
    to the next workflow-resolution layer.

    It does NOT itself resume or execute a workflow.
    """

    review_id: str

    approved: bool
    rejected: bool

    can_continue: bool

    reviewer: Optional[str] = None
    comments: str = ""

    reason: Optional[str] = None


class AIHumanReviewResolutionService:
    """
    Deterministically resolves an AI human-review decision.

    Security / governance guarantees:

    1. The decision must belong to the review being resolved.
    2. Only pending reviews may be resolved.
    3. The review must genuinely require human review.
    4. Approval and rejection are mutually exclusive.
    5. Only approval can authorize continuation.
    6. BLOCK governance outcomes cannot be overridden here.
    """

    REVIEW_OUTCOME = "REVIEW"
    PENDING_STATUS = "PENDING"

    @classmethod
    def resolve(
        cls,
        review: AIHumanReviewRequest,
        decision: AIHumanReviewDecision,
    ) -> AIHumanReviewResolution:

        cls._validate_types(
            review=review,
            decision=decision,
        )

        cls._validate_review(
            review
        )

        cls._validate_decision(
            decision
        )

        cls._validate_review_identity(
            review=review,
            decision=decision,
        )

        approved = bool(
            decision.approved
        )

        rejected = not approved

        if approved:

            return AIHumanReviewResolution(
                review_id=str(
                    review.review_id
                ),
                approved=True,
                rejected=False,
                can_continue=True,
                reviewer=decision.reviewer,
                comments=decision.comments or "",
                reason="Human review approved.",
            )

        return AIHumanReviewResolution(
            review_id=str(
                review.review_id
            ),
            approved=False,
            rejected=True,
            can_continue=False,
            reviewer=decision.reviewer,
            comments=decision.comments or "",
            reason="Human review rejected.",
        )

    # ---------------------------------------------------------
    # Validation
    # ---------------------------------------------------------

    @classmethod
    def _validate_types(
        cls,
        review,
        decision,
    ):

        if not isinstance(
            review,
            AIHumanReviewRequest,
        ):
            raise AIHumanReviewResolutionError(
                "review must be an AIHumanReviewRequest."
            )

        if not isinstance(
            decision,
            AIHumanReviewDecision,
        ):
            raise AIHumanReviewResolutionError(
                "decision must be an AIHumanReviewDecision."
            )

    @classmethod
    def _validate_review(
        cls,
        review: AIHumanReviewRequest,
    ):

        if str(
            review.governance_outcome
        ).upper() != cls.REVIEW_OUTCOME:

            raise AIHumanReviewResolutionError(
                "Only REVIEW governance outcomes "
                "may be resolved by human review."
            )

        if not review.requires_review:

            raise AIHumanReviewResolutionError(
                "Review request does not require "
                "human review."
            )

        if str(
            review.status
        ).upper() != cls.PENDING_STATUS:

            raise AIHumanReviewResolutionError(
                "Only pending AI reviews may be resolved."
            )

    @classmethod
    def _validate_decision(
        cls,
        decision: AIHumanReviewDecision,
    ):

        if decision.approved not in (
            True,
            False,
        ):
            raise AIHumanReviewResolutionError(
                "Review decision must explicitly "
                "approve or reject the review."
            )

    @classmethod
    def _validate_review_identity(
        cls,
        review: AIHumanReviewRequest,
        decision: AIHumanReviewDecision,
    ):

        review_id = str(
            review.review_id
        )

        decision_review_id = str(
            decision.review_id
        )

        if review_id != decision_review_id:

            raise AIHumanReviewResolutionError(
                "Review decision does not belong "
                "to the supplied review request."
            )