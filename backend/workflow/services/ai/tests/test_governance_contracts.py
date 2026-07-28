from dataclasses import FrozenInstanceError

from django.test import SimpleTestCase

from workflow.services.ai.governance import (
    AIGovernancePolicy,
    AIGovernanceDecision,
)


class AIGovernanceContractTests(
    SimpleTestCase
):

    def test_policy_defaults(self):

        policy = AIGovernancePolicy()

        self.assertFalse(
            policy.allow_automation
        )

        self.assertEqual(
            policy.minimum_confidence,
            0.70,
        )

    def test_decision_can_execute(self):

        decision = AIGovernanceDecision(
            outcome="allow",
            allowed=True,
            requires_review=False,
            blocked=False,
        )

        self.assertTrue(
            decision.can_execute
        )

    def test_review_cannot_execute(self):

        decision = AIGovernanceDecision(
            outcome="review",
            allowed=True,
            requires_review=True,
            blocked=False,
        )

        self.assertFalse(
            decision.can_execute
        )

    def test_block_cannot_execute(self):

        decision = AIGovernanceDecision(
            outcome="block",
            allowed=False,
            requires_review=False,
            blocked=True,
        )

        self.assertFalse(
            decision.can_execute
        )

    def test_decision_is_immutable(self):

        decision = AIGovernanceDecision(
            outcome="block",
            allowed=False,
            requires_review=False,
            blocked=True,
        )

        with self.assertRaises(
            FrozenInstanceError
        ):
            decision.outcome = "allow"