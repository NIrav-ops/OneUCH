from workflow.services.ai.exceptions import ProviderNotFound

from workflow.services.ai.providers.mock import MockAIProvider
from workflow.services.ai.providers.openai import OpenAIProvider


class AIProviderRouter:

    PROVIDERS = {
        "mock": MockAIProvider,
        "openai": OpenAIProvider,
    }

    @classmethod
    def get_provider(cls, name="mock"):

        provider = cls.PROVIDERS.get(name)

        if provider is None:
            raise ProviderNotFound(
                f"Unknown AI provider '{name}'."
            )

        return provider()