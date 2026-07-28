from dataclasses import dataclass
from typing import Optional

from workflow.services.ai.exceptions import (
    AIValidationError,
)


@dataclass(frozen=True)
class AINodeConfiguration:
    """
    Normalized configuration for a workflow AI node.

    WorkflowNode.configuration is an untrusted JSON boundary.
    This class converts that dictionary into a predictable
    internal contract.
    """

    prompt: str

    provider: str = "mock"

    model: Optional[str] = None

    temperature: float = 0.0

    max_tokens: Optional[int] = 1000

    response_type: str = "text"

    fail_on_error: bool = True

    include_runtime_context: bool = True

    @classmethod
    def from_dict(
        cls,
        configuration,
        *,
        default_prompt,
    ):
        if configuration is None:
            configuration = {}

        if not isinstance(
            configuration,
            dict,
        ):
            raise AIValidationError(
                "AI node configuration must be a dictionary."
            )

        prompt = configuration.get(
            "prompt",
            default_prompt,
        )

        provider = configuration.get(
            "provider",
            "mock",
        )

        model = configuration.get(
            "model"
        )

        temperature = configuration.get(
            "temperature",
            0.0,
        )

        max_tokens = configuration.get(
            "max_tokens",
            1000,
        )

        response_type = configuration.get(
            "response_type",
            "text",
        )

        fail_on_error = configuration.get(
            "fail_on_error",
            True,
        )

        include_runtime_context = (
            configuration.get(
                "include_runtime_context",
                True,
            )
        )

        if not isinstance(prompt, str):
            raise AIValidationError(
                "AI node prompt must be a string."
            )

        if not prompt.strip():
            raise AIValidationError(
                "AI node prompt cannot be empty."
            )

        if not isinstance(provider, str):
            raise AIValidationError(
                "AI node provider must be a string."
            )

        if not provider.strip():
            raise AIValidationError(
                "AI node provider cannot be empty."
            )

        if (
            model is not None
            and not isinstance(model, str)
        ):
            raise AIValidationError(
                "AI node model must be a string or null."
            )

        if not isinstance(
            temperature,
            (int, float),
        ):
            raise AIValidationError(
                "AI node temperature must be numeric."
            )

        if (
            temperature < 0
            or temperature > 2
        ):
            raise AIValidationError(
                "AI node temperature must be between 0 and 2."
            )

        if (
            max_tokens is not None
            and (
                not isinstance(max_tokens, int)
                or isinstance(max_tokens, bool)
                or max_tokens <= 0
            )
        ):
            raise AIValidationError(
                "AI node max_tokens must be a positive integer or null."
            )

        if not isinstance(
            response_type,
            str,
        ):
            raise AIValidationError(
                "AI node response_type must be a string."
            )

        if not isinstance(
            fail_on_error,
            bool,
        ):
            raise AIValidationError(
                "AI node fail_on_error must be boolean."
            )

        if not isinstance(
            include_runtime_context,
            bool,
        ):
            raise AIValidationError(
                "AI node include_runtime_context must be boolean."
            )

        return cls(
            prompt=prompt.strip(),
            provider=provider.strip(),
            model=(
                model.strip()
                if isinstance(model, str)
                else model
            ),
            temperature=float(
                temperature
            ),
            max_tokens=max_tokens,
            response_type=(
                response_type.strip()
            ),
            fail_on_error=(
                fail_on_error
            ),
            include_runtime_context=(
                include_runtime_context
            ),
        )