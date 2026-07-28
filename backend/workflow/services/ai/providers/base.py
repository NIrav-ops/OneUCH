from abc import ABC, abstractmethod

from workflow.services.ai.contracts import (
    AIRequest,
    AIResult,
)
from workflow.services.ai.validator import (
    AIRequestValidator,
)


class BaseAIProvider(ABC):
    """
    Base contract implemented by every One UCH AI provider.

    Provider implementations must translate AIRequest into their
    provider-specific request and normalize their response into
    AIResult.
    """

    provider_name = None

    def validate_request(
        self,
        request: AIRequest,
    ):
        return AIRequestValidator.validate(
            request
        )

    @abstractmethod
    def execute(
        self,
        request: AIRequest,
    ) -> AIResult:
        """
        Execute an AI request and return a normalized AIResult.
        """

        raise NotImplementedError