from django.test import SimpleTestCase

from workflow.services.ai.review import (
    AIHumanReviewDecision,
    AIHumanReviewRequest,
    AIHumanReviewResolutionError,
    AIHumanReviewResolutionService,
)


class AIHumanReviewResolutionTests(
    SimpleTestCase
):

    def _build_review(
        self,
        **overrides,
    ):

        values = {
            "workflow_instance_id":
                "WF-100",

            "workflow_node_id":
                "NODE-10",

            "governance_outcome":
                "REVIEW",

            "confidence":
                0.82,

            "policy_name":
                "high_risk",

            "reason":
                "Human approval required",

            "response_type":
                "summary",

            "ai_output": {
                "summary":
                    "Invoice approved",
            },
        }

        values.update(
            overrides
        )

        return AIHumanReviewRequest(
            **values
        )

    def _build_decision(
        self,
        review,
        approved=True,
        **overrides,
    ):

        values = {
            "review_id":
                str(review.review_id),

            "approved":
                approved,

            "reviewer":
                "reviewer@example.com",

            "comments":
                "Reviewed by human.",
        }

        values.update(
            overrides
        )

        return AIHumanReviewDecision(
            **values
        )

    # ---------------------------------------------------------
    # Approval
    # ---------------------------------------------------------

    def test_approved_review_can_continue(
        self,
    ):

        review = self._build_review()

        decision = self._build_decision(
            review,
            approved=True,
        )

        resolution = (
            AIHumanReviewResolutionService.resolve(
                review=review,
                decision=decision,
            )
        )

        self.assertTrue(
            resolution.approved
        )

        self.assertFalse(
            resolution.rejected
        )

        self.assertTrue(
            resolution.can_continue
        )

        self.assertEqual(
            resolution.review_id,
            str(review.review_id),
        )

    # ---------------------------------------------------------
    # Rejection
    # ---------------------------------------------------------

    def test_rejected_review_cannot_continue(
        self,
    ):

        review = self._build_review()

        decision = self._build_decision(
            review,
            approved=False,
        )

        resolution = (
            AIHumanReviewResolutionService.resolve(
                review=review,
                decision=decision,
            )
        )

        self.assertFalse(
            resolution.approved
        )

        self.assertTrue(
            resolution.rejected
        )

        self.assertFalse(
            resolution.can_continue
        )

    # ---------------------------------------------------------
    # Review identity protection
    # ---------------------------------------------------------

    def test_wrong_review_id_is_rejected(
        self,
    ):

        review = self._build_review()

        decision = self._build_decision(
            review,
            review_id="WRONG-REVIEW-ID",
        )

        with self.assertRaises(
            AIHumanReviewResolutionError
        ):

            AIHumanReviewResolutionService.resolve(
                review=review,
                decision=decision,
            )

    # ---------------------------------------------------------
    # BLOCK must never be converted into review approval
    # ---------------------------------------------------------

    def test_block_outcome_cannot_be_resolved(
        self,
    ):

        review = self._build_review(
            governance_outcome="BLOCK",
        )

        decision = self._build_decision(
            review,
            approved=True,
        )

        with self.assertRaises(
            AIHumanReviewResolutionError
        ):

            AIHumanReviewResolutionService.resolve(
                review=review,
                decision=decision,
            )

    # ---------------------------------------------------------
    # Type safety
    # ---------------------------------------------------------

    def test_invalid_review_type_is_rejected(
        self,
    ):

        review = self._build_review()

        decision = self._build_decision(
            review
        )

        with self.assertRaises(
            AIHumanReviewResolutionError
        ):

            AIHumanReviewResolutionService.resolve(
                review={},
                decision=decision,
            )

    def test_invalid_decision_type_is_rejected(
        self,
    ):

        review = self._build_review()

        with self.assertRaises(
            AIHumanReviewResolutionError
        ):

            AIHumanReviewResolutionService.resolve(
                review=review,
                decision={},
            )