from django.test import SimpleTestCase

from workflow.services.ai.contracts import (
    AIRequest,
    AIResult,
)


class AIContractTests(SimpleTestCase):

    def test_ai_request_defaults(self):

        request = AIRequest(
            prompt="Summarize this email"
        )

        self.assertEqual(
            request.prompt,
            "Summarize this email",
        )

        self.assertEqual(
            request.temperature,
            0.0,
        )

        self.assertEqual(
            request.response_type,
            "text",
        )

        self.assertEqual(
            request.variables,
            {},
        )

        self.assertEqual(
            request.context,
            {},
        )

        self.assertEqual(
            request.metadata,
            {},
        )

    def test_ai_result_success(self):

        result = AIResult(
            success=True,
            output="Completed",
            provider="mock",
        )

        self.assertTrue(
            result.success
        )

        self.assertFalse(
            result.failed
        )

        self.assertEqual(
            result.output,
            "Completed",
        )

    def test_ai_result_failed_property(self):

        result = AIResult(
            success=False,
            error="Provider failed",
        )

        self.assertTrue(
            result.failed
        )

    def test_mutable_defaults_are_isolated(self):

        first = AIRequest(
            prompt="First"
        )

        second = AIRequest(
            prompt="Second"
        )

        first.context["customer"] = "ABC"

        self.assertEqual(
            second.context,
            {},
        )