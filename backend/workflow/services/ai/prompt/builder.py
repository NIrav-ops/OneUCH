"""
Enterprise Prompt Builder.

Provides two supported construction paths:

1. build()
   Backward-compatible prompt construction used by existing
   workflow executors.

2. build_from_template()
   Enterprise template-based construction using the prompt
   registry, validator, and renderer.
"""

from copy import deepcopy
from typing import Any

from workflow.services.ai.prompt.templates import (
    SYSTEM_PROMPT,
)
from workflow.services.ai.prompt.registry import (
    PromptRegistry,
)
from workflow.services.ai.prompt.renderer import (
    PromptRenderer,
)
from workflow.services.ai.prompt.validator import (
    PromptValidator,
)


class PromptBuilder:

    @classmethod
    def build(
        cls,
        task_prompt: str,
        context: Any = None,
    ) -> str:
        """
        Backward-compatible prompt builder.

        Existing workflow code currently depends on this method
        returning one final prompt string.

        Do not remove this API until workflow execution has been
        migrated to build_from_template().
        """

        prompt_parts = [
            SYSTEM_PROMPT,
        ]

        if context:
            prompt_parts.append(
                "Enterprise Context:\n"
                f"{context}"
            )

        prompt_parts.append(
            str(task_prompt)
        )

        return "\n\n".join(
            prompt_parts
        )

    @classmethod
    def build_from_template(
        cls,
        template_name: str,
        variables: dict | None = None,
        context: dict | None = None,
    ) -> dict:
        """
        Build a structured enterprise prompt.

        Returns provider-independent prompt data that can later
        be converted into an AIRequest.
        """

        variables = deepcopy(
            variables or {}
        )

        context = deepcopy(
            context or {}
        )

        template = PromptRegistry.get(
            template_name
        )

        PromptValidator.validate(
            template
        )

        cls._validate_required_variables(
            template=template,
            variables=variables,
        )

        system_prompt = PromptRenderer.render(
            template["system"],
            variables,
        )

        user_prompt = PromptRenderer.render(
            template["user"],
            variables,
        )

        return {
            "name": template["name"],
            "version": template.get(
                "version",
                "1.0",
            ),
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "response_type": template[
                "response_type"
            ],
            "context": context,
            "metadata": deepcopy(
                template.get(
                    "metadata",
                    {},
                )
            ),
        }

    @staticmethod
    def _validate_required_variables(
        template: dict,
        variables: dict,
    ):
        """
        Validate variables explicitly declared by the template.

        PromptRenderer separately validates placeholders that
        actually occur in the rendered strings.
        """

        required_variables = set(
            template.get(
                "required_variables",
                [],
            )
        )

        supplied_variables = set(
            variables.keys()
        )

        missing = (
            required_variables
            - supplied_variables
        )

        if missing:
            from workflow.services.ai.exceptions import (
                AIValidationError,
            )

            raise AIValidationError(
                "Missing required prompt variables: "
                + ", ".join(
                    sorted(missing)
                )
            )