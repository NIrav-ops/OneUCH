"""
Enterprise Prompt Registry.

Provides a single place to retrieve prompt definitions.
"""

from workflow.services.ai.prompt.templates import (
    SUMMARY_PROMPT,
    CLASSIFICATION_PROMPT,
    ACTION_EXTRACTION_PROMPT,
)


PROMPTS = {
    SUMMARY_PROMPT["name"]: SUMMARY_PROMPT,
    CLASSIFICATION_PROMPT["name"]: CLASSIFICATION_PROMPT,
    ACTION_EXTRACTION_PROMPT["name"]: ACTION_EXTRACTION_PROMPT,
}


class PromptRegistry:

    @classmethod
    def get(cls, name: str):

        try:
            return PROMPTS[name]

        except KeyError:

            raise ValueError(
                f"Unknown prompt template '{name}'."
            )

    @classmethod
    def exists(cls, name: str):

        return name in PROMPTS

    @classmethod
    def list(cls):

        return sorted(PROMPTS.keys())