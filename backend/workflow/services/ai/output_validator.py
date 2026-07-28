from numbers import Number
from typing import Any

from workflow.services.ai.contracts import (
    AIRequest,
    AIResult,
)

from workflow.services.ai.exceptions import (
    AIOutputValidationError,
)


class AIOutputValidator:
    """
    Validates normalized AI provider output against the response
    contract requested by the caller.

    AI/provider output must be treated as untrusted data.

    This validator intentionally performs deterministic structural
    validation only. Business-specific semantic validation belongs
    in later domain layers.
    """

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
    def validate(
        cls,
        request: AIRequest,
        result: AIResult,
    ) -> bool:

        if not isinstance(request, AIRequest):
            raise AIOutputValidationError(
                "request must be an AIRequest instance"
            )

        if not isinstance(result, AIResult):
            raise AIOutputValidationError(
                "result must be an AIResult instance"
            )

        # Failed provider executions do not contain trustworthy
        # output to validate. Their failure is handled by the
        # execution service.
        if not result.success:
            return True

        response_type = request.response_type

        if response_type not in cls.SUPPORTED_RESPONSE_TYPES:
            raise AIOutputValidationError(
                f"Unsupported response_type: {response_type}"
            )

        output = result.output

        validators = {
            "text": cls._validate_text,
            "json": cls._validate_json,
            "boolean": cls._validate_boolean,
            "number": cls._validate_number,
            "classification": cls._validate_classification,
            "summary": cls._validate_summary,
            "decision": cls._validate_decision,
            "action_list": cls._validate_action_list,
            "approval_recommendation":
                cls._validate_approval_recommendation,
        }

        validator = validators[response_type]

        validator(output)

        cls._validate_response_schema(
            request=request,
            output=output,
        )

        return True

    @staticmethod
    def _validate_text(
        output: Any,
    ) -> None:

        if not isinstance(output, str):
            raise AIOutputValidationError(
                "AI text response must be a string."
            )

    @staticmethod
    def _validate_json(
        output: Any,
    ) -> None:

        if not isinstance(
            output,
            (dict, list),
        ):
            raise AIOutputValidationError(
                "AI JSON response must be a dictionary or list."
            )

    @staticmethod
    def _validate_boolean(
        output: Any,
    ) -> None:

        if not isinstance(output, bool):
            raise AIOutputValidationError(
                "AI boolean response must be a boolean."
            )

    @staticmethod
    def _validate_number(
        output: Any,
    ) -> None:

        # bool is a subclass of int in Python and therefore must
        # be explicitly rejected.
        if (
            isinstance(output, bool)
            or not isinstance(output, Number)
        ):
            raise AIOutputValidationError(
                "AI number response must be numeric."
            )

    @staticmethod
    def _validate_classification(
        output: Any,
    ) -> None:

        if not isinstance(output, dict):
            raise AIOutputValidationError(
                "AI classification response must be a dictionary."
            )

        label = output.get("label")

        if (
            not isinstance(label, str)
            or not label.strip()
        ):
            raise AIOutputValidationError(
                "AI classification response requires a non-empty label."
            )

        confidence = output.get(
            "confidence"
        )

        if confidence is not None:

            if (
                isinstance(confidence, bool)
                or not isinstance(
                    confidence,
                    Number,
                )
            ):
                raise AIOutputValidationError(
                    "Classification confidence must be numeric."
                )

            if (
                confidence < 0
                or confidence > 1
            ):
                raise AIOutputValidationError(
                    "Classification confidence must be between 0 and 1."
                )

    @staticmethod
    def _validate_summary(
        output: Any,
    ) -> None:

        if not isinstance(output, dict):
            raise AIOutputValidationError(
                "AI summary response must be a dictionary."
            )

        summary = output.get(
            "summary"
        )

        if (
            not isinstance(summary, str)
            or not summary.strip()
        ):
            raise AIOutputValidationError(
                "AI summary response requires a non-empty summary."
            )

    @staticmethod
    def _validate_decision(
        output: Any,
    ) -> None:

        if not isinstance(output, dict):
            raise AIOutputValidationError(
                "AI decision response must be a dictionary."
            )

        decision = output.get(
            "decision"
        )

        if (
            not isinstance(decision, str)
            or not decision.strip()
        ):
            raise AIOutputValidationError(
                "AI decision response requires a non-empty decision."
            )

    @staticmethod
    def _validate_action_list(
        output: Any,
    ) -> None:

        if not isinstance(output, dict):
            raise AIOutputValidationError(
                "AI action_list response must be a dictionary."
            )

        actions = output.get(
            "actions"
        )

        if not isinstance(actions, list):
            raise AIOutputValidationError(
                "AI action_list response requires an actions list."
            )

        for index, action in enumerate(
            actions
        ):

            if not isinstance(
                action,
                dict,
            ):
                raise AIOutputValidationError(
                    f"Action at index {index} must be a dictionary."
                )

    @staticmethod
    def _validate_approval_recommendation(
        output: Any,
    ) -> None:

        if not isinstance(output, dict):
            raise AIOutputValidationError(
                "AI approval recommendation must be a dictionary."
            )

        recommendation = output.get(
            "recommendation"
        )

        if (
            not isinstance(
                recommendation,
                str,
            )
            or not recommendation.strip()
        ):
            raise AIOutputValidationError(
                "AI approval recommendation requires a non-empty recommendation."
            )

    @staticmethod
    def _validate_response_schema(
        request: AIRequest,
        output: Any,
    ) -> None:
        """
        Minimal schema enforcement for the current foundation.

        Full JSON Schema support should be introduced separately
        rather than partially implementing the JSON Schema
        specification here.
        """

        schema = request.response_schema

        if schema is None:
            return

        if not isinstance(output, dict):
            raise AIOutputValidationError(
                "response_schema requires dictionary output."
            )

        required_fields = schema.get(
            "required",
            [],
        )

        if not isinstance(
            required_fields,
            list,
        ):
            raise AIOutputValidationError(
                "response_schema.required must be a list."
            )

        for field_name in required_fields:

            if not isinstance(
                field_name,
                str,
            ):
                raise AIOutputValidationError(
                    "response_schema required field names must be strings."
                )

            if field_name not in output:
                raise AIOutputValidationError(
                    f"AI response is missing required field: {field_name}"
                )