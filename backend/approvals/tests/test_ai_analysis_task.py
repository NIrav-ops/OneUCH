from datetime import (
    datetime,
    timedelta,
    timezone as dt_timezone,
)
from unittest.mock import patch

from django.contrib.auth import (
    get_user_model,
)
from django.test import (
    TestCase,
    override_settings,
)
from django.utils import timezone

from approvals.models import (
    ApprovalItem,
    AIApprovalCandidate,
    AIApprovalAnalysisState,
)
from approvals.services.ai_extractor import (
    AIApprovalExtractionResult,
)
from approvals.tasks import (
    analyze_new_approvals,
)
from email_accounts.models import (
    EmailAccount,
)
from inbox.models import (
    InboxMessage,
    Organization,
)


User = get_user_model()


AI_SETTINGS = {
    "APPROVAL_AI_ENABLED": True,
    "ONEUCH_AI_PROVIDER": "mock",
    "ONEUCH_AI_MODEL": "mock-model",
    "APPROVAL_AI_AUTO_CREATE_THRESHOLD": 95,
    "APPROVAL_AI_REVIEW_THRESHOLD": 85,
    "APPROVAL_AI_MAX_ATTEMPTS": 3,
    "APPROVAL_AI_RETRY_BASE_SECONDS": 300,
    "APPROVAL_AI_RETRY_MAX_SECONDS": 3600,
}


class ApprovalAIAnalysisTaskTests(
    TestCase
):

    def setUp(self):
        self.user = User.objects.create_user(
            email="approval-ai-worker@test.com",
            password="pass123",
        )

        self.organization = (
            Organization.objects.create(
                name="Approval AI Worker Test",
                slug="approval-ai-worker-test",
            )
        )

        self.allowed_account = (
            EmailAccount.objects.create(
                user=self.user,
                account_type="gmail",
                email_address=(
                    "approval-ai-allowed@test.com"
                ),
                is_active=True,
            )
        )

        self.blocked_account = (
            EmailAccount.objects.create(
                user=self.user,
                account_type="outlook",
                email_address=(
                    "approval-ai-blocked@test.com"
                ),
                is_active=True,
            )
        )

    def create_message(
        self,
        *,
        external_message_id,
        body,
        email_account=None,
    ):
        return InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            email_account=(
                email_account
                or self.allowed_account
            ),
            platform="gmail",
            direction="inbound",
            external_message_id=(
                external_message_id
            ),
            sender="customer@example.com",
            recipients=self.user.email,
            subject="Authorization request",
            body=body,
            received_at=datetime(
                2026,
                8,
                25,
                5,
                0,
                tzinfo=dt_timezone.utc,
            ),
            approval_analyzed=False,
        )

    @patch(
        "approvals.tasks."
        "extract_approvals_with_ai_result"
    )
    @override_settings(
        **AI_SETTINGS
    )
    def test_deterministic_hit_does_not_call_ai(
        self,
        ai_mock,
    ):
        message = self.create_message(
            external_message_id=(
                "approval-ai-deterministic-001"
            ),
            body=(
                "Please approve the production "
                "deployment."
            ),
        )

        with self.settings(
            APPROVAL_AI_ALLOWED_ACCOUNT_IDS={
                self.allowed_account.id,
            }
        ):
            processed = (
                analyze_new_approvals.run(
                    message_ids=[
                        message.id
                    ]
                )
            )

        self.assertEqual(
            processed,
            1,
        )

        ai_mock.assert_not_called()

        approval = (
            ApprovalItem.objects.get(
                message=message,
            )
        )

        self.assertEqual(
            approval.source_type,
            "email",
        )

    @patch(
        "approvals.tasks."
        "extract_approvals_with_ai_result"
    )
    @override_settings(
        **AI_SETTINGS
    )
    def test_high_confidence_ai_creates_approval(
        self,
        ai_mock,
    ):
        message = self.create_message(
            external_message_id=(
                "approval-ai-auto-001"
            ),
            body=(
                "Are you comfortable with us "
                "moving ahead with production?"
            ),
        )

        ai_mock.return_value = (
            AIApprovalExtractionResult(
                success=True,
                candidates=[
                    {
                        "title": (
                            "Authorize production"
                        ),
                        "description": (
                            "Provide authorization "
                            "to proceed."
                        ),
                        "priority": 90,
                        "approver_reference": (
                            "Rakesh"
                        ),
                        "due_date": None,
                        "confidence_score": 98,
                        "evidence": (
                            "Are you comfortable with "
                            "us moving ahead with "
                            "production?"
                        ),
                        "reason": (
                            "Authorization requested."
                        ),
                        "provider": "openai",
                        "model": "gpt-5.6-luna",
                    }
                ],
                provider="openai",
                model="gpt-5.6-luna",
            )
        )

        with self.settings(
            APPROVAL_AI_ALLOWED_ACCOUNT_IDS={
                self.allowed_account.id,
            }
        ):
            processed = (
                analyze_new_approvals.run(
                    message_ids=[
                        message.id
                    ]
                )
            )

        self.assertEqual(
            processed,
            1,
        )

        approval = (
            ApprovalItem.objects.get(
                message=message,
            )
        )

        self.assertEqual(
            approval.source_type,
            "ai",
        )

        self.assertEqual(
            approval.confidence_score,
            98,
        )

        self.assertIsNone(
            approval.assigned_to
        )

        self.assertFalse(
            AIApprovalCandidate.objects.filter(
                message=message,
            ).exists()
        )

    @patch(
        "approvals.tasks."
        "extract_approvals_with_ai_result"
    )
    @override_settings(
        **AI_SETTINGS
    )
    def test_review_confidence_creates_candidate(
        self,
        ai_mock,
    ):
        message = self.create_message(
            external_message_id=(
                "approval-ai-review-001"
            ),
            body=(
                "Would you be okay if we "
                "move ahead?"
            ),
        )

        ai_mock.return_value = (
            AIApprovalExtractionResult(
                success=True,
                candidates=[
                    {
                        "title": (
                            "Authorize moving ahead"
                        ),
                        "description": "",
                        "priority": 80,
                        "approver_reference": (
                            "Rakesh"
                        ),
                        "due_date": None,
                        "confidence_score": 90,
                        "evidence": (
                            "Would you be okay if "
                            "we move ahead?"
                        ),
                        "reason": (
                            "Possible authorization "
                            "request."
                        ),
                        "provider": "openai",
                        "model": "gpt-5.6-luna",
                    }
                ],
                provider="openai",
                model="gpt-5.6-luna",
            )
        )

        with self.settings(
            APPROVAL_AI_ALLOWED_ACCOUNT_IDS={
                self.allowed_account.id,
            }
        ):
            processed = (
                analyze_new_approvals.run(
                    message_ids=[
                        message.id
                    ]
                )
            )

        self.assertEqual(
            processed,
            1,
        )

        self.assertFalse(
            ApprovalItem.objects.filter(
                message=message,
            ).exists()
        )

        candidate = (
            AIApprovalCandidate.objects.get(
                message=message,
            )
        )

        self.assertEqual(
            candidate.status,
            "pending_review",
        )

        self.assertEqual(
            candidate.confidence_score,
            90,
        )

        self.assertEqual(
            candidate.approver_reference,
            "Rakesh",
        )

    @patch(
        "approvals.tasks."
        "extract_approvals_with_ai_result"
    )
    @override_settings(
        **AI_SETTINGS
    )
    def test_ai_failure_creates_retry_state(
        self,
        ai_mock,
    ):
        message = self.create_message(
            external_message_id=(
                "approval-ai-failure-001"
            ),
            body=(
                "Need your green light before "
                "we move ahead."
            ),
        )

        ai_mock.return_value = (
            AIApprovalExtractionResult(
                success=False,
                candidates=[],
                error="Provider unavailable",
                provider="openai",
                model="gpt-5.6-luna",
            )
        )

        with self.settings(
            APPROVAL_AI_ALLOWED_ACCOUNT_IDS={
                self.allowed_account.id,
            }
        ):
            processed = (
                analyze_new_approvals.run(
                    message_ids=[
                        message.id
                    ]
                )
            )

        self.assertEqual(
            processed,
            0,
        )

        state = (
            AIApprovalAnalysisState.objects.get(
                message=message,
            )
        )

        self.assertEqual(
            state.attempt_count,
            1,
        )

        self.assertEqual(
            state.status,
            "retry_wait",
        )

        message.refresh_from_db()

        self.assertFalse(
            message.approval_analyzed
        )

    @patch(
        "approvals.tasks."
        "extract_approvals_with_ai_result"
    )
    @override_settings(
        **AI_SETTINGS
    )
    def test_retry_wait_skips_provider(
        self,
        ai_mock,
    ):
        message = self.create_message(
            external_message_id=(
                "approval-ai-retry-wait-001"
            ),
            body=(
                "Need your green light before "
                "we move ahead."
            ),
        )

        AIApprovalAnalysisState.objects.create(
            message=message,
            organization=self.organization,
            attempt_count=1,
            status="retry_wait",
            next_retry_at=(
                timezone.now()
                + timedelta(
                    minutes=5
                )
            ),
        )

        with self.settings(
            APPROVAL_AI_ALLOWED_ACCOUNT_IDS={
                self.allowed_account.id,
            }
        ):
            processed = (
                analyze_new_approvals.run(
                    message_ids=[
                        message.id
                    ]
                )
            )

        self.assertEqual(
            processed,
            0,
        )

        ai_mock.assert_not_called()

        message.refresh_from_db()

        self.assertFalse(
            message.approval_analyzed
        )

    @patch(
        "approvals.tasks."
        "extract_approvals_with_ai_result"
    )
    @override_settings(
        **AI_SETTINGS
    )
    def test_successful_retry_clears_state(
        self,
        ai_mock,
    ):
        message = self.create_message(
            external_message_id=(
                "approval-ai-retry-success-001"
            ),
            body=(
                "Need your green light before "
                "we move ahead."
            ),
        )

        AIApprovalAnalysisState.objects.create(
            message=message,
            organization=self.organization,
            attempt_count=1,
            status="retry_wait",
            next_retry_at=(
                timezone.now()
                - timedelta(
                    seconds=1
                )
            ),
        )

        ai_mock.return_value = (
            AIApprovalExtractionResult(
                success=True,
                candidates=[],
                provider="openai",
                model="gpt-5.6-luna",
            )
        )

        with self.settings(
            APPROVAL_AI_ALLOWED_ACCOUNT_IDS={
                self.allowed_account.id,
            }
        ):
            processed = (
                analyze_new_approvals.run(
                    message_ids=[
                        message.id
                    ]
                )
            )

        self.assertEqual(
            processed,
            1,
        )

        self.assertFalse(
            AIApprovalAnalysisState.objects.filter(
                message=message,
            ).exists()
        )

        message.refresh_from_db()

        self.assertTrue(
            message.approval_analyzed
        )

    @patch(
        "approvals.tasks."
        "extract_approvals_with_ai_result"
    )
    @override_settings(
        **AI_SETTINGS
    )
    def test_non_allowed_account_does_not_call_ai(
        self,
        ai_mock,
    ):
        message = self.create_message(
            external_message_id=(
                "approval-ai-blocked-001"
            ),
            body=(
                "Need your green light before "
                "we move ahead."
            ),
            email_account=(
                self.blocked_account
            ),
        )

        with self.settings(
            APPROVAL_AI_ALLOWED_ACCOUNT_IDS={
                self.allowed_account.id,
            }
        ):
            processed = (
                analyze_new_approvals.run(
                    message_ids=[
                        message.id
                    ]
                )
            )

        self.assertEqual(
            processed,
            1,
        )

        ai_mock.assert_not_called()

        message.refresh_from_db()

        self.assertTrue(
            message.approval_analyzed
        )

        self.assertFalse(
            ApprovalItem.objects.filter(
                message=message,
            ).exists()
        )

    @patch(
        "approvals.tasks."
        "extract_approvals_with_ai_result"
    )
    @override_settings(
        **AI_SETTINGS
    )
    def test_successful_ai_no_approval_marks_analyzed(
        self,
        ai_mock,
    ):
        message = self.create_message(
            external_message_id=(
                "approval-ai-none-001"
            ),
            body=(
                "Sharing this for your "
                "information only."
            ),
        )

        ai_mock.return_value = (
            AIApprovalExtractionResult(
                success=True,
                candidates=[],
                provider="openai",
                model="gpt-5.6-luna",
            )
        )

        with self.settings(
            APPROVAL_AI_ALLOWED_ACCOUNT_IDS={
                self.allowed_account.id,
            }
        ):
            processed = (
                analyze_new_approvals.run(
                    message_ids=[
                        message.id
                    ]
                )
            )

        self.assertEqual(
            processed,
            1,
        )

        message.refresh_from_db()

        self.assertTrue(
            message.approval_analyzed
        )

        self.assertFalse(
            ApprovalItem.objects.filter(
                message=message,
            ).exists()
        )
