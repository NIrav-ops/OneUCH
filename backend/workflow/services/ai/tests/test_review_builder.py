from django.test import SimpleTestCase

from workflow.services.ai.contracts import (
    AIRequest,
    AIResult,
)

from workflow.services.ai.governance import (
    AIGovernanceDecision,
)

from workflow.services.ai.review import (
    AIHumanReviewBuilder,
    AIHumanReviewRequest,
)


class AIHumanReviewBuilderTests(
    SimpleTestCase
):

    def _build_request(self):

        return AIRequest(
            prompt="Analyze invoice",
            response_type="summary",
            metadata={
                "workflow_instance_id":
                    "WF-100",

                "workflow_node_id":
                    "NODE-10",
            },
        )

    def _build_result(self):

        return AIResult(
            success=True,
            output={
                "summary":
                    "Invoice approved",
            },
            provider="mock",
            model="mock-model",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            execution_time_ms=100,
            cost=0.01,
            confidence=0.82,
        )

    def _build_governance(self):

        return AIGovernanceDecision(
            outcome="REVIEW",
            allowed=False,
            requires_review=True,
            blocked=False,
            confidence=0.82,
            reason=(
                "Human approval required"
            ),
            policy_name="high_risk",
        )

    def test_build_returns_review_request(
        self,
    ):

        review = (
            AIHumanReviewBuilder.build(
                request=(
                    self._build_request()
                ),
                result=(
                    self._build_result()
                ),
                governance=(
                    self._build_governance()
                ),
            )
        )

        self.assertIsInstance(
            review,
            AIHumanReviewRequest,
        )

    def test_build_preserves_workflow_identity(
        self,
    ):

        review = (
            AIHumanReviewBuilder.build(
                request=(
                    self._build_request()
                ),
                result=(
                    self._build_result()
                ),
                governance=(
                    self._build_governance()
                ),
            )
        )

        self.assertEqual(
            review.workflow_instance_id,
            "WF-100",
        )

        self.assertEqual(
            review.workflow_node_id,
            "NODE-10",
        )

    def test_build_preserves_governance(
        self,
    ):

        review = (
            AIHumanReviewBuilder.build(
                request=(
                    self._build_request()
                ),
                result=(
                    self._build_result()
                ),
                governance=(
                    self._build_governance()
                ),
            )
        )

        self.assertEqual(
            review.governance_outcome,
            "REVIEW",
        )

        self.assertEqual(
            review.confidence,
            0.82,
        )

        self.assertEqual(
            review.policy_name,
            "high_risk",
        )

        self.assertEqual(
            review.reason,
            "Human approval required",
        )

        self.assertTrue(
            review.requires_review
        )

    def test_build_preserves_ai_output(
        self,
    ):

        review = (
            AIHumanReviewBuilder.build(
                request=(
                    self._build_request()
                ),
                result=(
                    self._build_result()
                ),
                governance=(
                    self._build_governance()
                ),
            )
        )

        self.assertEqual(
            review.response_type,
            "summary",
        )

        self.assertEqual(
            review.ai_output,
            {
                "summary":
                    "Invoice approved",
            },
        )

    def test_build_enriches_metadata(
        self,
    ):

        review = (
            AIHumanReviewBuilder.build(
                request=(
                    self._build_request()
                ),
                result=(
                    self._build_result()
                ),
                governance=(
                    self._build_governance()
                ),
            )
        )

        metadata = review.metadata

        self.assertEqual(
            metadata["provider"],
            "mock",
        )

        self.assertEqual(
            metadata["model"],
            "mock-model",
        )

        self.assertTrue(
            metadata["success"]
        )

        self.assertEqual(
            metadata["prompt_tokens"],
            10,
        )

        self.assertEqual(
            metadata[
                "completion_tokens"
            ],
            5,
        )

        self.assertEqual(
            metadata["total_tokens"],
            15,
        )

        self.assertEqual(
            metadata["cost"],
            0.01,
        )

        self.assertEqual(
            metadata["execution_time"],
            0.1,
        )

        self.assertEqual(
            metadata[
                "governance_policy"
            ],
            "high_risk",
        )

        self.assertEqual(
            metadata[
                "governance_outcome"
            ],
            "REVIEW",
        )

    def test_review_is_serializable(
        self,
    ):

        review = (
            AIHumanReviewBuilder.build(
                request=(
                    self._build_request()
                ),
                result=(
                    self._build_result()
                ),
                governance=(
                    self._build_governance()
                ),
            )
        )

        data = review.serialize()

        self.assertIsInstance(
            data,
            dict,
        )

        self.assertEqual(
            data["status"],
            "PENDING",
        )

        self.assertEqual(
            data["review_type"],
            "AI_GOVERNANCE",
        )

        self.assertTrue(
            data["requires_review"]
        )

        self.assertEqual(
            data["ai_output"],
            {
                "summary":
                    "Invoice approved",
            },
        )