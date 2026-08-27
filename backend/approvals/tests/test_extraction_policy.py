from django.test import SimpleTestCase

from approvals.services.extraction_policy import (
    decide_ai_approval,
)


class ApprovalExtractionPolicyTests(
    SimpleTestCase
):

    def test_95_auto_creates(
        self,
    ):
        result = decide_ai_approval(
            confidence_score=95,
        )

        self.assertEqual(
            result.decision,
            "auto_create",
        )

    def test_100_auto_creates(
        self,
    ):
        result = decide_ai_approval(
            confidence_score=100,
        )

        self.assertEqual(
            result.decision,
            "auto_create",
        )

    def test_94_requires_review(
        self,
    ):
        result = decide_ai_approval(
            confidence_score=94,
        )

        self.assertEqual(
            result.decision,
            "review",
        )

    def test_85_requires_review(
        self,
    ):
        result = decide_ai_approval(
            confidence_score=85,
        )

        self.assertEqual(
            result.decision,
            "review",
        )

    def test_84_is_ignored(
        self,
    ):
        result = decide_ai_approval(
            confidence_score=84,
        )

        self.assertEqual(
            result.decision,
            "ignore",
        )

    def test_confidence_is_clamped(
        self,
    ):
        high = decide_ai_approval(
            confidence_score=150,
        )

        low = decide_ai_approval(
            confidence_score=-20,
        )

        self.assertEqual(
            high.confidence_score,
            100,
        )

        self.assertEqual(
            low.confidence_score,
            0,
        )

    def test_custom_thresholds_are_supported(
        self,
    ):
        result = decide_ai_approval(
            confidence_score=90,
            auto_create_threshold=92,
            review_threshold=80,
        )

        self.assertEqual(
            result.decision,
            "review",
        )
