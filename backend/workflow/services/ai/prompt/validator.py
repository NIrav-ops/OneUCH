"""
Prompt validation utilities.
"""

from workflow.services.ai.exceptions import (
    AIValidationError,
)


class PromptValidator:

    @classmethod
    def validate(
        cls,
        prompt: dict,
    ):

        required = [
            "name",
            "system",
            "user",
            "response_type",
            "required_variables",
        ]

        for field in required:

            if field not in prompt:

                raise AIValidationError(
                    f"Prompt missing '{field}'."
                )

        return True