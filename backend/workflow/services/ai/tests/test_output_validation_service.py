from unittest.mock import patch

from django.test import SimpleTestCase

from workflow.services.ai.contracts import (
    AIRequest,
    AIResult,
)

from workflow.services.ai.service import (
    AIExecutionService,
)


class AIOutputValidationServiceTests(
    SimpleTestCase
):

    @patch(
        "workflow.services.ai.providers.mock."
        "MockAIProvider.execute"
    )
    def test_valid_provider_output_passes(
        self,
        execute_mock,
    ):

        execute_mock.return_value = (
            AIResult(
                success=True,
                output={
                    "summary":
                        "Valid summary"
                },
                provider="mock",
                model="mock-model",
            )
        )

        result = (
            AIExecutionService.execute(
                AIRequest(
                    prompt="Summarize",
                    response_type="summary",
                ),
                provider="mock",
            )
        )

        self.assertTrue(
            result.success
        )

        self.assertEqual(
            result.output["summary"],
            "Valid summary",
        )

    @patch(
        "workflow.services.ai.providers.mock."
        "MockAIProvider.execute"
    )
    def test_invalid_provider_output_fails_closed(
        self,
        execute_mock,
    ):

        execute_mock.return_value = (
            AIResult(
                success=True,
                output=(
                    "This should have "
                    "been structured"
                ),
                provider="mock",
                model="mock-model",
            )
        )

        result = (
            AIExecutionService.execute(
                AIRequest(
                    prompt="Summarize",
                    response_type="summary",
                ),
                provider="mock",
            )
        )

        self.assertFalse(
            result.success
        )

        self.assertIsNone(
            result.output
        )

        self.assertEqual(
            result.metadata[
                "failure_stage"
            ],
            "output_validation",
        )

        self.assertEqual(
            result.metadata[
                "exception_type"
            ],
            "AIOutputValidationError",
        )

    @patch(
        "workflow.services.ai.providers.mock."
        "MockAIProvider.execute"
    )
    def test_schema_violation_fails_closed(
        self,
        execute_mock,
    ):

        execute_mock.return_value = (
            AIResult(
                success=True,
                output={
                    "decision": "approve"
                },
                provider="mock",
                model="mock-model",
            )
        )

        result = (
            AIExecutionService.execute(
                AIRequest(
                    prompt="Decide",
                    response_type="json",
                    response_schema={
                        "required": [
                            "decision",
                            "reason",
                        ]
                    },
                ),
                provider="mock",
            )
        )

        self.assertFalse(
            result.success
        )

        self.assertEqual(
            result.metadata[
                "failure_stage"
            ],
            "output_validation",
        )