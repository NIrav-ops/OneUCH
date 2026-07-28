from django.test import TestCase

from workflow.services.ai.prompt.registry import PromptRegistry


class PromptRegistryTests(TestCase):

    def test_summary_exists(self):

        self.assertTrue(
            PromptRegistry.exists(
                "summary"
            )
        )

    def test_registry_returns_prompt(self):

        prompt = PromptRegistry.get(
            "summary"
        )

        self.assertEqual(
            prompt["name"],
            "summary",
        )

    def test_list_contains_summary(self):

        prompts = PromptRegistry.list()

        self.assertIn(
            "summary",
            prompts,
        )

    def test_unknown_prompt(self):

        with self.assertRaises(ValueError):

            PromptRegistry.get(
                "does_not_exist"
            )