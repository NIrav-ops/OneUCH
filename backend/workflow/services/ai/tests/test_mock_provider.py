from django.test import TestCase

from workflow.services.ai.models import AIRequest
from workflow.services.ai.providers.mock import MockAIProvider


class MockProviderTests(TestCase):

    def test_execute(self):

        provider = MockAIProvider()

        result = provider.execute(
            AIRequest(
                prompt="Hello",
                response_type="summary",
            )
        )

        self.assertTrue(result.success)

        self.assertEqual(
            result.provider,
            "mock",
        )

        self.assertEqual(
            result.output["summary"],
            "Mock Summary",
        )