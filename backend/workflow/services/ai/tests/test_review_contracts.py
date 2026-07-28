from django.test import SimpleTestCase

from workflow.services.ai.review import (
    AIHumanReviewRequest,
    AIHumanReviewDecision,
)


class AIHumanReviewContractTests(
    SimpleTestCase
):

    def test_review_request_defaults(self):

        review = AIHumanReviewRequest(
            workflow_instance_id="WF-100",
            workflow_node_id="NODE-10",
            governance_outcome="REVIEW",
            confidence=0.82,
            policy_name="high_risk",
            reason="Human approval required",
            response_type="summary",
            ai_output={
                "summary":
                    "Invoice approved",
            },
        )

        self.assertIsNotNone(
            review.review_id
        )

        self.assertEqual(
            review.workflow_instance_id,
            "WF-100",
        )

        self.assertEqual(
            review.workflow_node_id,
            "NODE-10",
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
            review.review_type,
            "AI_GOVERNANCE",
        )

        self.assertEqual(
            review.status,
            "PENDING",
        )

        self.assertTrue(
            review.requires_review
        )

    def test_review_request_serialization(self):

        review = AIHumanReviewRequest(
            workflow_instance_id="WF-100",
            workflow_node_id="NODE-10",
            governance_outcome="REVIEW",
            confidence=0.75,
            policy_name="default",
            reason="Review required",
            response_type="summary",
            ai_output={
                "summary": "Test",
            },
            metadata={
                "source": "unit-test",
            },
        )

        data = review.serialize()

        self.assertIsInstance(
            data,
            dict,
        )

        self.assertEqual(
            data["workflow_instance_id"],
            "WF-100",
        )

        self.assertEqual(
            data["workflow_node_id"],
            "NODE-10",
        )

        self.assertEqual(
            data["status"],
            "PENDING",
        )

        self.assertEqual(
            data["review_type"],
            "AI_GOVERNANCE",
        )

        self.assertEqual(
            data["metadata"]["source"],
            "unit-test",
        )

        self.assertIn(
            "review_id",
            data,
        )

        self.assertIn(
            "created_at",
            data,
        )

    def test_review_decision_approved(self):

        decision = AIHumanReviewDecision(
            review_id="REVIEW-100",
            approved=True,
            comments="Approved by reviewer",
        )

        self.assertEqual(
            decision.review_id,
            "REVIEW-100",
        )

        self.assertTrue(
            decision.approved
        )

        self.assertFalse(
            decision.rejected
        )

        data = decision.serialize()

        self.assertEqual(
            data["review_id"],
            "REVIEW-100",
        )

        self.assertTrue(
            data["approved"]
        )

        self.assertFalse(
            data["rejected"]
        )

        self.assertEqual(
            data["comments"],
            "Approved by reviewer",
        )

    def test_review_decision_rejected(self):

        decision = AIHumanReviewDecision(
            review_id="REVIEW-101",
            approved=False,
            comments="Rejected after review",
        )

        self.assertEqual(
            decision.review_id,
            "REVIEW-101",
        )

        self.assertFalse(
            decision.approved
        )

        self.assertTrue(
            decision.rejected
        )

        data = decision.serialize()

        self.assertEqual(
            data["review_id"],
            "REVIEW-101",
        )

        self.assertFalse(
            data["approved"]
        )

        self.assertTrue(
            data["rejected"]
        )

        self.assertEqual(
            data["comments"],
            "Rejected after review",
        )