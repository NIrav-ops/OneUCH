from workflow.services.ai.governance.contracts import (
    AIGovernancePolicy,
)


class AIGovernancePolicyRegistry:
    """
    Central registry for deterministic AI governance policies.

    Policies are application-owned and must never be controlled
    by the AI provider or AI-generated output.
    """

    POLICIES = {
        "default": AIGovernancePolicy(
            allow_automation=False,
            minimum_confidence=0.70,
            automatic_execution_confidence=0.90,
            require_review_below=0.90,
            block_below=0.50,
        ),

        "advisory": AIGovernancePolicy(
            allow_automation=False,
            minimum_confidence=0.0,
            automatic_execution_confidence=1.0,
            require_review_below=1.0,
            block_below=0.0,
        ),

        "high_risk": AIGovernancePolicy(
            allow_automation=False,
            minimum_confidence=0.85,
            automatic_execution_confidence=1.0,
            require_review_below=1.0,
            block_below=0.70,
            require_human_review=True,
        ),

        "controlled_automation": AIGovernancePolicy(
            allow_automation=True,
            minimum_confidence=0.75,
            automatic_execution_confidence=0.95,
            require_review_below=0.95,
            block_below=0.60,
        ),
    }

    @classmethod
    def get(
        cls,
        name="default",
    ):

        policy = cls.POLICIES.get(
            name
        )

        if policy is None:
            raise ValueError(
                "Unknown AI governance policy: "
                f"'{name}'."
            )

        return policy