from unittest.mock import patch

from django.test import SimpleTestCase

from workflow.services.ai.models import (
    AIRequest,
)

from workflow.services.ai.service import (
    AIExecutionService,
)

from workflow.services.ai.exceptions import (
    InvalidAIRequest,
    ProviderNotFound,
)


class AIExecutionHardeningTests(
    SimpleTestCase
):

    def test_invalid_empty_prompt_rejected(self):

        request = AIRequest(
            prompt="",
        )

        with self.assertRaises(
            InvalidAIRequest
        ):
            AIExecutionService.execute(
                request
            )

    def test_invalid_temperature_rejected(self):

        request = AIRequest(
            prompt="Test",
            temperature=3.0,
        )

        with self.assertRaises(
            InvalidAIRequest
        ):
            AIExecutionService.execute(
                request
            )

    def test_unknown_provider_rejected(self):

        request = AIRequest(
            prompt="Test",
        )

        with self.assertRaises(
            ProviderNotFound
        ):
            AIExecutionService.execute(
                request,
                provider="unknown",
            )

    @patch(
        "workflow.services.ai.providers.mock."
        "MockAIProvider.execute"
    )
    def test_provider_exception_returns_failed_result(
        self,
        mock_execute,
    ):

        mock_execute.side_effect = (
            RuntimeError(
                "Provider unavailable"
            )
        )

        request = AIRequest(
            prompt="Test",
        )

        result = AIExecutionService.execute(
            request,
            provider="mock",
        )

        self.assertFalse(
            result.success
        )

        self.assertEqual(
            result.provider,
            "mock",
        )

        self.assertEqual(
            result.error,
            "Provider unavailable",
        )

        self.assertEqual(
            result.metadata[
                "exception_type"
            ],
            "RuntimeError",
        )