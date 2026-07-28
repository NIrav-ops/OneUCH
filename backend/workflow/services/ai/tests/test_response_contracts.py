from dataclasses import FrozenInstanceError

from django.test import SimpleTestCase

from workflow.services.ai.responses import (
    AIClassification,
    AISummary,
    AIDecision,
    AIActionRecommendation,
    AIActionList,
    AIApprovalRecommendation,
)


class AIResponseContractTests(
    SimpleTestCase
):

    def test_classification_contract(self):

        result = AIClassification(
            label="finance",
            confidence=0.9,
        )

        self.assertEqual(
            result.label,
            "finance",
        )

    def test_summary_contract(self):

        result = AISummary(
            summary="Payment requested.",
            key_points=[
                "Invoice attached",
            ],
        )

        self.assertEqual(
            len(result.key_points),
            1,
        )

    def test_decision_contract(self):

        result = AIDecision(
            decision="review_required",
            confidence=0.8,
        )

        self.assertEqual(
            result.decision,
            "review_required",
        )

    def test_action_contract(self):

        action = AIActionRecommendation(
            title="Review invoice",
            priority=80,
        )

        self.assertEqual(
            action.priority,
            80,
        )

    def test_action_list_contract(self):

        result = AIActionList(
            actions=[
                AIActionRecommendation(
                    title="Review invoice",
                )
            ]
        )

        self.assertEqual(
            len(result.actions),
            1,
        )

    def test_approval_contract(self):

        result = (
            AIApprovalRecommendation(
                recommendation="review",
            )
        )

        self.assertEqual(
            result.recommendation,
            "review",
        )

    def test_contract_is_immutable(self):

        result = AIClassification(
            label="finance",
        )

        with self.assertRaises(
            FrozenInstanceError
        ):
            result.label = "sales"