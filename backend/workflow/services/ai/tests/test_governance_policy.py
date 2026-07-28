from django.test import SimpleTestCase

from workflow.services.ai.governance import (
    AIGovernancePolicyRegistry,
)


class AIGovernancePolicyTests(
    SimpleTestCase
):

    def test_default_policy(self):

        policy = (
            AIGovernancePolicyRegistry.get(
                "default"
            )
        )

        self.assertFalse(
            policy.allow_automation
        )

    def test_high_risk_policy_requires_review(
        self,
    ):

        policy = (
            AIGovernancePolicyRegistry.get(
                "high_risk"
            )
        )

        self.assertTrue(
            policy.require_human_review
        )

    def test_controlled_automation_policy(
        self,
    ):

        policy = (
            AIGovernancePolicyRegistry.get(
                "controlled_automation"
            )
        )

        self.assertTrue(
            policy.allow_automation
        )

    def test_unknown_policy_rejected(self):

        with self.assertRaises(
            ValueError
        ):
            AIGovernancePolicyRegistry.get(
                "does-not-exist"
            )