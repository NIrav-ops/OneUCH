from django.test import TestCase

from workflow.services.ai.prompt.renderer import (
    PromptRenderer,
)
from workflow.services.ai.exceptions import (
    AIValidationError,
)


class PromptRendererTests(TestCase):

    def test_render(self):

        result = PromptRenderer.render(
            "Hello {name}",
            {
                "name": "John",
            },
        )

        self.assertEqual(
            result,
            "Hello John",
        )

    def test_missing_variable(self):

        with self.assertRaises(
            AIValidationError
        ):

            PromptRenderer.render(
                "Hello {name}",
                {},
            )