from django.test import TestCase

from workflow.services.ai.prompt.validator import (
    PromptValidator,
)


class PromptValidatorTests(TestCase):

    def test_validate(self):

        prompt = {
            "name": "summary",
            "system": "...",
            "user": "...",
            "response_type": "summary",
            "required_variables": [],
        }

        self.assertTrue(
            PromptValidator.validate(prompt)
        )