from workflow.services.ai.contracts import (
    AIRequest,
    AIResult,
)

from workflow.services.ai.governance.contracts import (
    AIGovernanceDecision,
)

from workflow.services.ai.governance.policy import (
    AIGovernancePolicyRegistry,
)


class AIGovernanceEngine:
    """
    Deterministically evaluates whether validated AI output
    may influence workflow execution.

    This engine never executes business operations.
    """

    OUTCOME_ALLOW = "allow"
    OUTCOME_REVIEW = "review"
    OUTCOME_BLOCK = "block"

    HIGH_RISK_RESPONSE_TYPES = {
        "decision",
        "approval_recommendation",
    }

    @classmethod
    def evaluate(
        cls,
        request: AIRequest,
        result: AIResult,
        policy_name="default",
    ) -> AIGovernanceDecision:

        policy = (
            AIGovernancePolicyRegistry.get(
                policy_name
            )
        )

        if not result.success:

            return cls._block(
                policy_name=policy_name,
                confidence=result.confidence,
                reason="AI execution failed.",
            )

        confidence = cls._normalize_confidence(
            result.confidence
        )

        if confidence < policy.block_below:

            return cls._block(
                policy_name=policy_name,
                confidence=confidence,
                reason=(
                    "AI confidence is below the "
                    "policy blocking threshold."
                ),
            )

        if (
            request.response_type
            in cls.HIGH_RISK_RESPONSE_TYPES
        ):

            return cls._review(
                policy_name=policy_name,
                confidence=confidence,
                reason=(
                    "AI response type requires "
                    "human review."
                ),
            )

        if policy.require_human_review:

            return cls._review(
                policy_name=policy_name,
                confidence=confidence,
                reason=(
                    "Governance policy requires "
                    "human review."
                ),
            )

        if confidence < policy.minimum_confidence:

            return cls._review(
                policy_name=policy_name,
                confidence=confidence,
                reason=(
                    "AI confidence is below the "
                    "minimum confidence threshold."
                ),
            )

        if not policy.allow_automation:

            return cls._review(
                policy_name=policy_name,
                confidence=confidence,
                reason=(
                    "AI automation is disabled "
                    "by governance policy."
                ),
            )

        if (
            confidence
            < policy.automatic_execution_confidence
        ):

            return cls._review(
                policy_name=policy_name,
                confidence=confidence,
                reason=(
                    "AI confidence is below the "
                    "automatic execution threshold."
                ),
            )

        return cls._allow(
            policy_name=policy_name,
            confidence=confidence,
            reason=(
                "AI result satisfies governance "
                "requirements."
            ),
        )

    @staticmethod
    def _normalize_confidence(
        confidence,
    ):

        if confidence is None:
            return 0.0

        try:
            confidence = float(
                confidence
            )
        except (
            TypeError,
            ValueError,
        ):
            return 0.0

        return max(
            0.0,
            min(
                confidence,
                1.0,
            ),
        )

    @classmethod
    def _allow(
        cls,
        policy_name,
        confidence,
        reason,
    ):

        return AIGovernanceDecision(
            outcome=cls.OUTCOME_ALLOW,
            allowed=True,
            requires_review=False,
            blocked=False,
            confidence=confidence,
            reason=reason,
            policy_name=policy_name,
        )

    @classmethod
    def _review(
        cls,
        policy_name,
        confidence,
        reason,
    ):

        return AIGovernanceDecision(
            outcome=cls.OUTCOME_REVIEW,
            allowed=True,
            requires_review=True,
            blocked=False,
            confidence=confidence,
            reason=reason,
            policy_name=policy_name,
        )

    @classmethod
    def _block(
        cls,
        policy_name,
        confidence,
        reason,
    ):

        return AIGovernanceDecision(
            outcome=cls.OUTCOME_BLOCK,
            allowed=False,
            requires_review=False,
            blocked=True,
            confidence=confidence,
            reason=reason,
            policy_name=policy_name,
        )