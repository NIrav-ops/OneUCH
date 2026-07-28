from django.test import SimpleTestCase

from workflow.services.ai.contracts import (
    AIRequest,
)

from workflow.services.ai.exceptions import (
    AIValidationError,
)

from workflow.services.ai.providers import (
    MockAIProvider,
)


class MockAIProviderTests(SimpleTestCase):

    def test_mock_provider_text_response(self):

        provider = MockAIProvider()

        request = AIRequest(
            prompt="Summarize this email"
        )

        result = provider.execute(
            request
        )

        self.assertTrue(
            result.success
        )

        self.assertEqual(
            result.provider,
            "mock",
        )

        self.assertEqual(
            result.model,
            "mock-model",
        )

        self.assertEqual(
            result.output,
            "Mock AI response",
        )

        self.assertEqual(
            result.cost,
            0.0,
        )

    def test_mock_provider_custom_output(self):

        provider = MockAIProvider(
            output={
                "summary": "Purchase approved",
            }
        )

        request = AIRequest(
            prompt="Summarize"
        )

        result = provider.execute(
            request
        )

        self.assertEqual(
            result.output,
            {
                "summary": "Purchase approved",
            },
        )

    def test_mock_provider_structured_summary(self):

        provider = MockAIProvider()

        request = AIRequest(
            prompt="Summarize",
            response_type="summary",
        )

        result = provider.execute(
            request
        )

        self.assertEqual(
            result.output,
            {
                "summary": "Mock Summary",
            },
        )

    def test_mock_provider_validates_request(self):

        provider = MockAIProvider()

        request = AIRequest(
            prompt=""
        )

        with self.assertRaises(
            AIValidationError
        ):
            provider.execute(
                request
            )