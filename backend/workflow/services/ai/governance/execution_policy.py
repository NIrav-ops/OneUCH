from dataclasses import dataclass


@dataclass(frozen=True)
class AIExecutionPolicyDecision:
    """
    Deterministic decision made BEFORE an AI provider
    receives any communication content.
    """

    allowed: bool
    mode: str
    provider: str
    reason: str


class AIExecutionPolicy:
    """
    Provider-access governance for One UCH.

    This policy answers a different question from
    AIGovernanceEngine:

        AIGovernanceEngine
        -> May validated AI output influence execution?

        AIExecutionPolicy
        -> May this provider receive the request at all?

    The AI provider never controls this decision.
    """

    MODE_DETERMINISTIC_ONLY = (
        "deterministic_only"
    )
    MODE_CLOUD = "cloud"
    MODE_LOCAL = "local"

    ALLOWED_PROVIDERS = {
        MODE_DETERMINISTIC_ONLY: set(),

        MODE_CLOUD: {
            "mock",
            "openai",
        },

        MODE_LOCAL: {
            "mock",
            "ollama",
        },
    }

    @classmethod
    def evaluate(
        cls,
        *,
        mode,
        provider,
    ):
        normalized_mode = (
            str(mode or "")
            .strip()
            .lower()
        )

        normalized_provider = (
            str(provider or "")
            .strip()
            .lower()
        )

        if (
            normalized_mode
            not in cls.ALLOWED_PROVIDERS
        ):
            return AIExecutionPolicyDecision(
                allowed=False,
                mode=normalized_mode,
                provider=normalized_provider,
                reason=(
                    "Unknown One UCH AI execution mode."
                ),
            )

        if (
            normalized_mode
            == cls.MODE_DETERMINISTIC_ONLY
        ):
            return AIExecutionPolicyDecision(
                allowed=False,
                mode=normalized_mode,
                provider=normalized_provider,
                reason=(
                    "Generative AI is disabled by "
                    "One UCH governance policy."
                ),
            )

        allowed_providers = (
            cls.ALLOWED_PROVIDERS[
                normalized_mode
            ]
        )

        if (
            normalized_provider
            not in allowed_providers
        ):
            return AIExecutionPolicyDecision(
                allowed=False,
                mode=normalized_mode,
                provider=normalized_provider,
                reason=(
                    f"AI provider "
                    f"'{normalized_provider}' "
                    f"is not permitted in "
                    f"'{normalized_mode}' mode."
                ),
            )

        return AIExecutionPolicyDecision(
            allowed=True,
            mode=normalized_mode,
            provider=normalized_provider,
            reason=(
                "AI provider is permitted by "
                "One UCH execution governance."
            ),
        )
