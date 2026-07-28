from workflow.services.ai.exceptions import ProviderNotFound

from workflow.services.ai.providers.mock import MockAIProvider


class AIProviderRouter:

    PROVIDERS = {
        "mock": MockAIProvider,
    }

    @classmethod
    def get_provider(cls, name="mock"):

        provider = cls.PROVIDERS.get(name)

        if provider is None:
            raise ProviderNotFound(
                f"Unknown AI provider '{name}'."
            )

        return provider()