"""
Enterprise Prompt Renderer.

Safely renders prompt templates using variables.
"""

import string

from workflow.services.ai.exceptions import (
    AIValidationError,
)


class PromptRenderer:

    @classmethod
    def render(
        cls,
        template: str,
        variables: dict | None = None,
    ) -> str:

        variables = variables or {}

        formatter = string.Formatter()

        required = {
            field_name
            for _, field_name, _, _
            in formatter.parse(template)
            if field_name
        }

        missing = required - variables.keys()

        if missing:
            raise AIValidationError(
                "Missing prompt variables: "
                + ", ".join(sorted(missing))
            )

        return template.format(**variables)