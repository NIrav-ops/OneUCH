from django.test import SimpleTestCase

from workflow.services.ai import PromptBuilder


class PromptBuilderTests(SimpleTestCase):

    def test_build_prompt_without_context(self):

        prompt = PromptBuilder.build(
            task_prompt="Summarize this email."
        )

        self.assertIn(
            "Summarize this email.",
            prompt,
        )

        self.assertIn(
            "Enterprise AI engine",
            prompt,
        )

    def test_build_prompt_with_context(self):

        prompt = PromptBuilder.build(
            task_prompt="Classify",
            context={
                "customer": "Cyberllix",
                "priority": "High",
            },
        )

        self.assertIn(
            "Cyberllix",
            prompt,
        )

        self.assertIn(
            "priority",
            prompt,
        )

        self.assertIn(
            "Classify",
            prompt,
        )