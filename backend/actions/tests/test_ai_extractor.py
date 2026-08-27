from unittest.mock import patch

from django.test import SimpleTestCase

from workflow.services.ai.contracts import (
    AIResult,
)

from actions.services.ai_extractor import (
    extract_actions_with_ai,
    extract_actions_with_ai_result,
)

from actions.services.ai_extractor import (
    ACTION_AI_PROMPT_VERSION,
    extract_actions_with_ai,
)


class AIActionExtractorTests(
    SimpleTestCase
):

    @patch(
        "actions.services.ai_extractor."
        "AIExecutionService.execute"
    )
    def test_semantic_action_is_returned(
        self,
        execute_mock,
    ):
        execute_mock.return_value = AIResult(
            success=True,
            provider="mock",
            model="mock-model",
            output={
                "actions": [
                    {
                        "title":
                            "Coordinate with finance",
                        "description":
                            "Coordinate with finance "
                            "and resolve the issue.",
                        "priority": 85,
                        "owner_reference": None,
                        "due_date": None,
                        "confidence": 0.94,
                        "metadata": {
                            "evidence":
                                "coordinate with finance "
                                "and get this sorted",
                            "reason":
                                "Explicit request.",
                        },
                    }
                ]
            },
        )

        actions = extract_actions_with_ai(
            subject="Customer issue",
            body=(
                "Please coordinate with finance "
                "and get this sorted."
            ),
            sender="customer@example.com",
            provider="mock",
            message_id=100,
        )

        self.assertEqual(
            len(actions),
            1,
        )

        self.assertEqual(
            actions[0]["title"],
            "Coordinate with finance",
        )

        self.assertEqual(
            actions[0][
                "confidence_score"
            ],
            94,
        )

        self.assertEqual(
            actions[0][
                "extraction_method"
            ],
            "ai",
        )

        self.assertEqual(
            actions[0][
                "prompt_version"
            ],
            ACTION_AI_PROMPT_VERSION,
        )

    @patch(
        "actions.services.ai_extractor."
        "AIExecutionService.execute"
    )
    def test_non_actionable_message_returns_empty(
        self,
        execute_mock,
    ):
        execute_mock.return_value = AIResult(
            success=True,
            provider="mock",
            model="mock-model",
            output={
                "actions": [],
            },
        )

        actions = extract_actions_with_ai(
            subject="Payment received",
            body=(
                "Payment has been received "
                "successfully for your records."
            ),
            provider="mock",
        )

        self.assertEqual(
            actions,
            [],
        )

    @patch(
        "actions.services.ai_extractor."
        "AIExecutionService.execute"
    )
    def test_hallucinated_evidence_is_rejected(
        self,
        execute_mock,
    ):
        execute_mock.return_value = AIResult(
            success=True,
            provider="mock",
            model="mock-model",
            output={
                "actions": [
                    {
                        "title":
                            "Send quotation",
                        "description":
                            "Send quotation tomorrow.",
                        "priority": 80,
                        "confidence": 0.99,
                        "metadata": {
                            "evidence":
                                "Please send quotation "
                                "tomorrow",
                        },
                    }
                ]
            },
        )

        actions = extract_actions_with_ai(
            subject="Meeting update",
            body=(
                "The customer meeting has "
                "been completed."
            ),
            provider="mock",
        )

        self.assertEqual(
            actions,
            [],
        )

    @patch(
        "actions.services.ai_extractor."
        "AIExecutionService.execute"
    )
    def test_provider_failure_is_fail_safe(
        self,
        execute_mock,
    ):
        execute_mock.return_value = AIResult(
            success=False,
            provider="mock",
            model="mock-model",
            error="Provider unavailable",
        )

        actions = extract_actions_with_ai(
            subject="Urgent",
            body=(
                "Please coordinate with finance."
            ),
            provider="mock",
        )

        self.assertEqual(
            actions,
            [],
        )

    @patch(
        "actions.services.ai_extractor."
        "AIExecutionService.execute"
    )
    def test_message_reference_time_is_sent_to_ai(
        self,
        execute_mock,
    ):
        from datetime import (
            datetime,
            timezone as dt_timezone,
        )

        execute_mock.return_value = AIResult(
            success=True,
            provider="mock",
            model="mock-model",
            output={
                "actions": [],
            },
        )

        reference_time = datetime(
            2026,
            8,
            25,
            10,
            30,
            tzinfo=dt_timezone.utc,
        )

        extract_actions_with_ai(
            subject="Deployment",
            body="Please resolve this tomorrow.",
            reference_time=reference_time,
            provider="mock",
        )

        request = (
            execute_mock.call_args.args[0]
        )

        self.assertIn(
            "2026-08-25T10:30:00+00:00",
            request.prompt,
        )

    @patch(
        "actions.services.ai_extractor."
        "AIExecutionService.execute"
    )
    def test_result_distinguishes_valid_no_action(
        self,
        execute_mock,
    ):
        execute_mock.return_value = AIResult(
            success=True,
            provider="mock",
            model="mock-model",
            output={
                "actions": [],
            },
        )

        result = extract_actions_with_ai_result(
            subject="FYI",
            body="For your information only.",
            provider="mock",
        )

        self.assertTrue(
            result.success
        )

        self.assertEqual(
            result.candidates,
            [],
        )

        self.assertIsNone(
            result.error
        )

    @patch(
        "actions.services.ai_extractor."
        "AIExecutionService.execute"
    )
    def test_result_distinguishes_provider_failure(
        self,
        execute_mock,
    ):
        execute_mock.return_value = AIResult(
            success=False,
            provider="mock",
            model="mock-model",
            output=None,
            error="Provider unavailable",
        )

        result = extract_actions_with_ai_result(
            subject="Customer issue",
            body="Can you get this sorted?",
            provider="mock",
        )

        self.assertFalse(
            result.success
        )

        self.assertEqual(
            result.candidates,
            [],
        )

        self.assertEqual(
            result.error,
            "Provider unavailable",
        )
