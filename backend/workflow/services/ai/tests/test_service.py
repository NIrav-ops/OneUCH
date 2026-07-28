from django.test import TestCase

from workflow.services.ai import (
    AIExecutionService,
    AIRequest,
)


class AIExecutionServiceTests(TestCase):

    def test_execute(self):

        result = AIExecutionService.execute(
            AIRequest(
                prompt="Summarize this email."
            )
        )

        self.assertTrue(result.success)

        self.assertEqual(
            result.provider,
            "mock",
        )