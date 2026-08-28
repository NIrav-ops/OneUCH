from unittest.mock import patch

from django.test import SimpleTestCase

from workflow.services.ai.contracts import (
    AIResult,
)

from actions.services.ai_extractor import (
    extract_actions_with_ai_result,
)


class ActionAIProcessingProvenanceTests(
    SimpleTestCase
):

    @patch(
        "actions.services.ai_extractor."
        "AIExecutionService.execute"
    )
    def test_candidate_carries_processing_mode(
        self,
        execute_mock,
    ):
        execute_mock.return_value = AIResult(
            success=True,
            provider="openai",
            model="test-model",
            metadata={
                "processing_mode":
                    "cloud",
            },
            output={
                "actions": [
                    {
                        "title":
                            "Send revised quotation",

                        "description":
                            "Send revised quotation.",

                        "priority": 80,

                        "owner_reference":
                            None,

                        "due_date":
                            None,

                        "confidence":
                            0.95,

                        "metadata": {
                            "evidence":
                                "send the revised quotation",

                            "reason":
                                "Explicit request.",
                        },
                    }
                ]
            },
        )

        result = extract_actions_with_ai_result(
            subject="Quotation",
            body=(
                "Please send the revised quotation."
            ),
            provider="openai",
        )

        self.assertTrue(
            result.success
        )

        self.assertEqual(
            result.processing_mode,
            "cloud",
        )

        self.assertEqual(
            result.candidates[0][
                "processing_mode"
            ],
            "cloud",
        )

        self.assertEqual(
            result.candidates[0][
                "provider"
            ],
            "openai",
        )
