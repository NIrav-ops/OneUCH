from django.test import SimpleTestCase

from workflow.services.ai import (
    AIRequest,
    AIResult,
)

from workflow.services.ai.governance import (
    AIGovernanceEngine,
)


class AIGovernanceEngineTests(
    SimpleTestCase
):

    def _request(
        self,
        response_type="summary",
    ):

        return AIRequest(
            prompt="Test",
            response_type=response_type,
        )

    def _result(
        self,
        confidence=1.0,
        success=True,
    ):

        return AIResult(
            success=success,
            output={},
            provider="mock",
            confidence=confidence,
        )

    def test_failed_ai_result_is_blocked(
        self,
    ):

        decision = (
            AIGovernanceEngine.evaluate(
                self._request(),
                self._result(
                    success=False
                ),
            )
        )

        self.assertTrue(
            decision.blocked
        )

    def test_low_confidence_is_blocked(
        self,
    ):

        decision = (
            AIGovernanceEngine.evaluate(
                self._request(),
                self._result(
                    confidence=0.30
                ),
            )
        )

        self.assertEqual(
            decision.outcome,
            "block",
        )

    def test_default_policy_requires_review(
        self,
    ):

        decision = (
            AIGovernanceEngine.evaluate(
                self._request(),
                self._result(
                    confidence=0.99
                ),
                policy_name="default",
            )
        )

        self.assertTrue(
            decision.requires_review
        )

        self.assertFalse(
            decision.can_execute
        )

    def test_controlled_automation_allows_high_confidence(
        self,
    ):

        decision = (
            AIGovernanceEngine.evaluate(
                self._request(),
                self._result(
                    confidence=0.99
                ),
                policy_name=(
                    "controlled_automation"
                ),
            )
        )

        self.assertEqual(
            decision.outcome,
            "allow",
        )

        self.assertTrue(
            decision.can_execute
        )

    def test_controlled_automation_requires_review_below_threshold(
        self,
    ):

        decision = (
            AIGovernanceEngine.evaluate(
                self._request(),
                self._result(
                    confidence=0.80
                ),
                policy_name=(
                    "controlled_automation"
                ),
            )
        )

        self.assertEqual(
            decision.outcome,
            "review",
        )

    def test_approval_recommendation_always_requires_review(
        self,
    ):

        decision = (
            AIGovernanceEngine.evaluate(
                self._request(
                    "approval_recommendation"
                ),
                self._result(
                    confidence=1.0
                ),
                policy_name=(
                    "controlled_automation"
                ),
            )
        )

        self.assertTrue(
            decision.requires_review
        )

        self.assertFalse(
            decision.can_execute
        )

    def test_decision_response_requires_review(
        self,
    ):

        decision = (
            AIGovernanceEngine.evaluate(
                self._request(
                    "decision"
                ),
                self._result(
                    confidence=1.0
                ),
                policy_name=(
                    "controlled_automation"
                ),
            )
        )

        self.assertEqual(
            decision.outcome,
            "review",
        )

    def test_none_confidence_is_safe(
        self,
    ):

        decision = (
            AIGovernanceEngine.evaluate(
                self._request(),
                self._result(
                    confidence=None
                ),
            )
        )

        self.assertTrue(
            decision.blocked
        )

    def test_confidence_above_one_is_normalized(
        self,
    ):

        decision = (
            AIGovernanceEngine.evaluate(
                self._request(),
                self._result(
                    confidence=5.0
                ),
                policy_name=(
                    "controlled_automation"
                ),
            )
        )

        self.assertEqual(
            decision.confidence,
            1.0,
        )

    def test_negative_confidence_is_normalized(
        self,
    ):

        decision = (
            AIGovernanceEngine.evaluate(
                self._request(),
                self._result(
                    confidence=-5.0
                ),
            )
        )

        self.assertEqual(
            decision.confidence,
            0.0,
        )

        self.assertTrue(
            decision.blocked
        )