from time import perf_counter
from typing import Any

from workflow.services.ai.contracts import (
    AIRequest,
    AIResult,
)
from workflow.services.ai.providers.base import (
    BaseAIProvider,
)


class MockAIProvider(BaseAIProvider):
    """
    Deterministic AI provider used for automated tests.

    No external API or network connection is required.
    """

    provider_name = "mock"
    default_model = "mock-model"

    def __init__(
        self,
        output: Any = None,
        confidence: float = 1.0,
    ):
        self.output = output
        self.confidence = confidence

    def execute(
        self,
        request: AIRequest,
    ) -> AIResult:

        self.validate_request(request)

        started_at = perf_counter()

        output = self.output

        if output is None:
            output = self._default_output(
                request
            )

        execution_time_ms = int(
            (
                perf_counter()
                - started_at
            )
            * 1000
        )

        return AIResult(
            success=True,
            output=output,
            provider=self.provider_name,
            model=request.model or self.default_model,
            execution_time_ms=execution_time_ms,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            cost=0.0,
            confidence=self.confidence,
            metadata={
                "mock": True,
                "response_type": request.response_type,
            },
        )

    @staticmethod
    def _default_output(
        request: AIRequest,
    ):

        response_type = request.response_type

        if response_type == "json":
            return {
                "result": "mock",
            }

        if response_type == "boolean":
            return True

        if response_type == "number":
            return 1

        if response_type == "classification":
            return {
                "label": "mock",
                "confidence": 1.0,
            }

        if response_type == "summary":
            return {
                "summary": "Mock Summary",
            }

        if response_type == "decision":
            return {
                "decision": "mock",
            }

        if response_type == "action_list":
            return {
                "actions": [],
            }

        if (
            response_type
            == "approval_recommendation"
        ):
            return {
                "recommendation": "approve",
            }

        return "Mock AI response"