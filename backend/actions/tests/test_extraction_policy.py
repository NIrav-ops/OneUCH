from django.test import SimpleTestCase

from actions.services.extraction_policy import (
    decide_ai_action,
)


class ActionExtractionPolicyTests(
    SimpleTestCase
):

    def test_high_confidence_requires_review(
        self,
    ):
        result = decide_ai_action(
            confidence_score=95,
            auto_create_threshold=90,
            review_threshold=75,
        )

        self.assertEqual(
            result.decision,
            "review",
        )

    def test_exact_former_auto_threshold_requires_review(
        self,
    ):
        result = decide_ai_action(
            confidence_score=90,
            auto_create_threshold=90,
            review_threshold=75,
        )

        self.assertEqual(
            result.decision,
            "review",
        )

    def test_review_band_requires_review(
        self,
    ):
        result = decide_ai_action(
            confidence_score=82,
            auto_create_threshold=90,
            review_threshold=75,
        )

        self.assertEqual(
            result.decision,
            "review",
        )

    def test_exact_review_threshold_requires_review(
        self,
    ):
        result = decide_ai_action(
            confidence_score=75,
            auto_create_threshold=90,
            review_threshold=75,
        )

        self.assertEqual(
            result.decision,
            "review",
        )

    def test_low_confidence_is_ignored(
        self,
    ):
        result = decide_ai_action(
            confidence_score=60,
            auto_create_threshold=90,
            review_threshold=75,
        )

        self.assertEqual(
            result.decision,
            "ignore",
        )

    def test_confidence_is_clamped_and_still_review_only(
        self,
    ):
        result = decide_ai_action(
            confidence_score=150,
            auto_create_threshold=90,
            review_threshold=75,
        )

        self.assertEqual(
            result.confidence_score,
            100,
        )

        self.assertEqual(
            result.decision,
            "review",
        )

    def test_auto_create_threshold_does_not_enable_creation(
        self,
    ):
        result = decide_ai_action(
            confidence_score=100,
            auto_create_threshold=1,
            review_threshold=75,
        )

        self.assertEqual(
            result.decision,
            "review",
        )
