from workflow.services.ai import AIRequest
from workflow.services.ai.exceptions import (
    InvalidAIRequest,
)


class AIRequestValidator:

    SUPPORTED_RESPONSE_TYPES = {
        "text",
        "json",
        "boolean",
        "number",
        "classification",
        "summary",
        "decision",
        "action_list",
        "approval_recommendation",
    }

    @classmethod
    def validate(cls, request):

        if not isinstance(request, AIRequest):
            raise InvalidAIRequest(
                "request must be an AIRequest instance"
            )

        if not request.prompt:
            raise InvalidAIRequest(
                "prompt is required"
            )

        if not request.prompt.strip():
            raise InvalidAIRequest(
                "prompt cannot be empty"
            )

        if request.temperature < 0 or request.temperature > 2:
            raise InvalidAIRequest(
                "temperature must be between 0 and 2"
            )

        if (
            request.max_tokens is not None
            and request.max_tokens <= 0
        ):
            raise InvalidAIRequest(
                "max_tokens must be greater than 0"
            )

        if request.response_type not in cls.SUPPORTED_RESPONSE_TYPES:
            raise InvalidAIRequest(
                f"Unsupported response_type: {request.response_type}"
            )

        return True


# ------------------------------------------------------------------
# Backward compatibility
# ------------------------------------------------------------------

class AIValidator(AIRequestValidator):
    """
    Legacy validator.
    """
    pass