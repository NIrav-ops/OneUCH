from django.test import SimpleTestCase

from workflow.services.ai.exceptions import (
    AIValidationError,
)
from workflow.services.ai.prompt.builder import (
    PromptBuilder,
)


class EnterprisePromptBuilderTests(
    SimpleTestCase
):

    def test_build_summary_template(self):

        result = (
            PromptBuilder.build_from_template(
                template_name="summary",
                variables={
                    "content": (
                        "Please review the purchase order."
                    ),
                },
            )
        )

        self.assertEqual(
            result["name"],
            "summary",
        )

        self.assertEqual(
            result["version"],
            "1.0",
        )

        self.assertEqual(
            result["response_type"],
            "summary",
        )

        self.assertIn(
            "Please review the purchase order.",
            result["user_prompt"],
        )

        self.assertIn(
            "Enterprise AI engine",
            result["system_prompt"],
        )

    def test_build_classification_template(self):

        result = (
            PromptBuilder.build_from_template(
                template_name="classification",
                variables={
                    "content": (
                        "Invoice requires finance approval."
                    ),
                },
            )
        )

        self.assertEqual(
            result["name"],
            "classification",
        )

        self.assertEqual(
            result["response_type"],
            "classification",
        )

    def test_build_action_extraction_template(self):

        result = (
            PromptBuilder.build_from_template(
                template_name="action_extraction",
                variables={
                    "content": (
                        "Please send the quotation tomorrow."
                    ),
                },
            )
        )

        self.assertEqual(
            result["response_type"],
            "action_list",
        )

        self.assertIn(
            "Please send the quotation tomorrow.",
            result["user_prompt"],
        )

    def test_context_is_preserved(self):

        context = {
            "organization_id": "org-1",
            "source": "workflow",
        }

        result = (
            PromptBuilder.build_from_template(
                template_name="summary",
                variables={
                    "content": "Test message",
                },
                context=context,
            )
        )

        self.assertEqual(
            result["context"],
            context,
        )

    def test_missing_required_variable_rejected(
        self,
    ):

        with self.assertRaises(
            AIValidationError
        ):
            PromptBuilder.build_from_template(
                template_name="summary",
                variables={},
            )

    def test_backward_compatible_build(self):

        result = PromptBuilder.build(
            task_prompt="Analyze this workflow.",
            context={
                "source": "workflow",
            },
        )

        self.assertIsInstance(
            result,
            str,
        )

        self.assertIn(
            "Enterprise AI engine",
            result,
        )

        self.assertIn(
            "Analyze this workflow.",
            result,
        )

        self.assertIn(
            "Enterprise Context:",
            result,
        )