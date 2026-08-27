from datetime import (
    datetime,
    timezone as dt_timezone,
)
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from approvals.services.ai_extractor import (
    extract_approvals_with_ai_result,
)


class ApprovalAIExtractorTests(
    SimpleTestCase
):

    def _success_result(
        self,
    ):
        return SimpleNamespace(
            success=True,
            error=None,
            provider="mock",
            model="mock-model",
        )

    def _parsed(
        self,
        *,
        title="Authorize production deployment",
        description=(
            "Provide authorization for the "
            "production deployment."
        ),
        priority=90,
        owner_reference=None,
        due_date=None,
        confidence=0.95,
        evidence=(
            "Are you comfortable with us "
            "moving ahead with production?"
        ),
        reason=(
            "The recipient is being asked "
            "for authorization to proceed."
        ),
    ):
        return SimpleNamespace(
            actions=[
                SimpleNamespace(
                    title=title,
                    description=description,
                    priority=priority,
                    owner_reference=(
                        owner_reference
                    ),
                    due_date=due_date,
                    confidence=confidence,
                    metadata={
                        "evidence": evidence,
                        "reason": reason,
                    },
                )
            ]
        )

    @patch(
        "approvals.services.ai_extractor."
        "AIResponseParser.parse"
    )
    @patch(
        "approvals.services.ai_extractor."
        "AIExecutionService.execute"
    )
    def test_semantic_approval_is_returned(
        self,
        execute_mock,
        parse_mock,
    ):
        execute_mock.return_value = (
            self._success_result()
        )

        parse_mock.return_value = (
            self._parsed()
        )

        result = (
            extract_approvals_with_ai_result(
                subject="Production deployment",
                body=(
                    "Are you comfortable with us "
                    "moving ahead with production?"
                ),
                provider="mock",
                model="mock-model",
            )
        )

        self.assertTrue(
            result.success
        )

        self.assertEqual(
            len(result.candidates),
            1,
        )

        candidate = (
            result.candidates[0]
        )

        self.assertEqual(
            candidate["title"],
            "Authorize production deployment",
        )

        self.assertEqual(
            candidate["confidence_score"],
            95,
        )

        self.assertEqual(
            candidate["extraction_method"],
            "ai",
        )

    @patch(
        "approvals.services.ai_extractor."
        "AIResponseParser.parse"
    )
    @patch(
        "approvals.services.ai_extractor."
        "AIExecutionService.execute"
    )
    def test_successful_no_approval_is_distinct(
        self,
        execute_mock,
        parse_mock,
    ):
        execute_mock.return_value = (
            self._success_result()
        )

        parse_mock.return_value = (
            SimpleNamespace(
                actions=[]
            )
        )

        result = (
            extract_approvals_with_ai_result(
                subject="FYI",
                body=(
                    "Sharing the deployment "
                    "update for information."
                ),
                provider="mock",
            )
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
        "approvals.services.ai_extractor."
        "AIExecutionService.execute"
    )
    def test_provider_failure_is_fail_safe(
        self,
        execute_mock,
    ):
        execute_mock.return_value = (
            SimpleNamespace(
                success=False,
                error="Provider unavailable",
                provider="mock",
                model="mock-model",
            )
        )

        result = (
            extract_approvals_with_ai_result(
                subject="Authorization",
                body=(
                    "Can you authorize this "
                    "production change?"
                ),
                provider="mock",
            )
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

    @patch(
        "approvals.services.ai_extractor."
        "AIResponseParser.parse"
    )
    @patch(
        "approvals.services.ai_extractor."
        "AIExecutionService.execute"
    )
    def test_hallucinated_evidence_is_rejected(
        self,
        execute_mock,
        parse_mock,
    ):
        execute_mock.return_value = (
            self._success_result()
        )

        parse_mock.return_value = (
            self._parsed(
                evidence=(
                    "Please approve the "
                    "production deployment."
                )
            )
        )

        result = (
            extract_approvals_with_ai_result(
                subject="Deployment",
                body=(
                    "Are you comfortable with us "
                    "moving ahead?"
                ),
                provider="mock",
            )
        )

        self.assertTrue(
            result.success
        )

        self.assertEqual(
            result.candidates,
            [],
        )

    @patch(
        "approvals.services.ai_extractor."
        "AIResponseParser.parse"
    )
    @patch(
        "approvals.services.ai_extractor."
        "AIExecutionService.execute"
    )
    def test_explicit_due_date_is_parsed(
        self,
        execute_mock,
        parse_mock,
    ):
        execute_mock.return_value = (
            self._success_result()
        )

        parse_mock.return_value = (
            self._parsed(
                due_date="2026-08-26",
                evidence=(
                    "Can you authorize the "
                    "deployment by 26 August 2026?"
                ),
            )
        )

        result = (
            extract_approvals_with_ai_result(
                subject="Deployment approval",
                body=(
                    "Can you authorize the "
                    "deployment by 26 August 2026?"
                ),
                provider="mock",
            )
        )

        self.assertTrue(
            result.success
        )

        self.assertEqual(
            result.candidates[
                0
            ]["due_date"].date().isoformat(),
            "2026-08-26",
        )

    @patch(
        "approvals.services.ai_extractor."
        "AIResponseParser.parse"
    )
    @patch(
        "approvals.services.ai_extractor."
        "AIExecutionService.execute"
    )
    def test_reference_time_is_in_prompt(
        self,
        execute_mock,
        parse_mock,
    ):
        execute_mock.return_value = (
            self._success_result()
        )

        parse_mock.return_value = (
            SimpleNamespace(
                actions=[]
            )
        )

        reference_time = datetime(
            2026,
            8,
            25,
            5,
            0,
            tzinfo=dt_timezone.utc,
        )

        extract_approvals_with_ai_result(
            subject="Deployment",
            body=(
                "Can you give us the go-ahead "
                "before tomorrow?"
            ),
            provider="mock",
            reference_time=reference_time,
        )

        request = (
            execute_mock.call_args.args[0]
        )

        self.assertIn(
            reference_time.isoformat(),
            request.prompt,
        )

    @patch(
        "approvals.services.ai_extractor."
        "AIResponseParser.parse"
    )
    @patch(
        "approvals.services.ai_extractor."
        "AIExecutionService.execute"
    )
    def test_approver_reference_is_normalized(
        self,
        execute_mock,
        parse_mock,
    ):
        execute_mock.return_value = (
            self._success_result()
        )

        parse_mock.return_value = (
            self._parsed(
                owner_reference="Rakesh",
                evidence=(
                    "Rakesh, are you comfortable "
                    "with us moving ahead with "
                    "production?"
                ),
            )
        )

        result = (
            extract_approvals_with_ai_result(
                subject="Production",
                body=(
                    "Rakesh, are you comfortable "
                    "with us moving ahead with "
                    "production?"
                ),
                provider="mock",
            )
        )

        self.assertEqual(
            result.candidates[
                0
            ]["approver_reference"],
            "Rakesh",
        )
