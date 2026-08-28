from unittest.mock import patch

from django.test import SimpleTestCase

from workflow.services.ai.contracts import (
    AIResult,
)

from approvals.services.ai_extractor import (
    extract_approvals_with_ai_result,
)


class ApprovalAIProcessingProvenanceTests(
    SimpleTestCase
):

    @patch(
        "approvals.services.ai_extractor."
        "AIExecutionService.execute"
    )
    def test_candidate_carries_processing_mode(
        self,
        execute_mock,
    ):
        execute_mock.return_value = AIResult(
            success=True,
            provider="ollama",
            model="local-model",
            metadata={
                "processing_mode":
                    "local",
            },
            output={
                "actions": [
                    {
                        "title":
                            "Authorize deployment",

                        "description":
                            "Authorize deployment.",

                        "priority": 90,

                        "owner_reference":
                            None,

                        "due_date":
                            None,

                        "confidence":
                            0.96,

                        "metadata": {
                            "evidence":
                                "approve the deployment",

                            "reason":
                                "Explicit approval request.",
                        },
                    }
                ]
            },
        )

        result = extract_approvals_with_ai_result(
            subject="Deployment",
            body=(
                "Please approve the deployment."
            ),
            provider="ollama",
        )

        self.assertTrue(
            result.success
        )

        self.assertEqual(
            result.processing_mode,
            "local",
        )

        self.assertEqual(
            result.candidates[0][
                "processing_mode"
            ],
            "local",
        )

        self.assertEqual(
            result.candidates[0][
                "provider"
            ],
            "ollama",
        )
