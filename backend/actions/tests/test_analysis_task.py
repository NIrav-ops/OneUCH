from datetime import datetime, timezone as dt_timezone

from django.contrib.auth import get_user_model
from unittest.mock import patch

from django.test import (
    TestCase,
    override_settings,
)

from actions.models import (
    ActionItem,
    AIActionCandidate,
    AIActionAnalysisState,
)

from actions.tasks import analyze_new_messages
from inbox.models import InboxMessage, Organization

from email_accounts.models import (
    EmailAccount,
)


User = get_user_model()


class ActionAnalysisTaskTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="action-task@test.com",
            password="pass123",
        )

        self.organization = Organization.objects.create(
            name="Action Task Test",
            slug="action-task-test",
        )

        self.allowed_account = (
            EmailAccount.objects.create(
                user=self.user,
                account_type="gmail",
                email_address=(
                    "allowed-ai@test.com"
                ),
                is_active=True,
            )
        )

        self.blocked_account = (
            EmailAccount.objects.create(
                user=self.user,
                account_type="gmail",
                email_address=(
                    "blocked-ai@test.com"
                ),
                is_active=True,
            )
        )

        self.ai_account_override = (
            override_settings(
                ACTION_AI_ALLOWED_ACCOUNT_IDS={
                    self.allowed_account.id,
                }
            )
        )

        self.ai_account_override.enable()

        self.addCleanup(
            self.ai_account_override.disable
        )

    def test_analysis_persists_extracted_due_date(self):
        received_at = datetime(
            2026,
            8,
            24,
            10,
            0,
            tzinfo=dt_timezone.utc,
        )

        message = InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            email_account=self.allowed_account,
            platform="gmail",
            direction="inbound",
            external_message_id="action-due-001",
            sender="customer@example.com",
            recipients=self.user.email,
            subject="Quotation required",
            body=(
                "Please send the revised quotation "
                "by Friday."
            ),
            received_at=received_at,
            action_analyzed=False,
        )

        processed = analyze_new_messages.run()

        self.assertEqual(processed, 1)

        action = ActionItem.objects.get(
            message=message,
        )

        self.assertEqual(
            action.title,
            "Send Quotation",
        )

        self.assertIsNotNone(
            action.due_date
        )

        self.assertEqual(
            action.due_date.date().isoformat(),
            "2026-08-28",
        )

        message.refresh_from_db()

        self.assertTrue(
            message.action_analyzed
        )

    def test_reanalysis_does_not_duplicate_action(self):
        message = InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            email_account=self.allowed_account,
            platform="gmail",
            direction="inbound",
            external_message_id="action-dedupe-001",
            sender="customer@example.com",
            recipients=self.user.email,
            subject="Contract review required",
            body=(
                "Please review the attached contract."
            ),
            received_at=datetime(
                2026,
                8,
                24,
                10,
                0,
                tzinfo=dt_timezone.utc,
            ),
            action_analyzed=False,
        )

        analyze_new_messages.run()

        self.assertEqual(
            ActionItem.objects.filter(
                message=message,
            ).count(),
            1,
        )

        message.action_analyzed = False
        message.save(
            update_fields=["action_analyzed"]
        )

        analyze_new_messages.run()

        self.assertEqual(
            ActionItem.objects.filter(
                message=message,
            ).count(),
            1,
        )

    @override_settings(
        ACTION_AI_ENABLED=False,
    )    
    def test_action_analysis_does_not_create_followup(self):
        from actions.models import FollowUpItem

        message = InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            email_account=self.allowed_account,
            platform="gmail",
            direction="inbound",
            external_message_id="action-only-001",
            sender="customer@example.com",
            recipients=self.user.email,
            subject="Waiting for your reply",
            body="Please reply when possible.",
            received_at=datetime(
                2026,
                8,
                24,
                10,
                0,
                tzinfo=dt_timezone.utc,
            ),
            action_analyzed=False,
        )

        processed = analyze_new_messages.run()

        self.assertEqual(processed, 1)

        self.assertFalse(
            ActionItem.objects.filter(
                message=message,
            ).exists()
        )

        self.assertFalse(
            FollowUpItem.objects.filter(
                last_message=message,
            ).exists()
        )

        message.refresh_from_db()

        self.assertTrue(
            message.action_analyzed
        )

    def test_analysis_can_target_specific_message_ids(self):
        target = InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            email_account=self.allowed_account,
            platform="gmail",
            direction="inbound",
            external_message_id="target-action-001",
            sender="customer@example.com",
            recipients=self.user.email,
            subject="Quotation required",
            body="Please send the revised quotation by Friday.",
            received_at=datetime(
                2026,
                8,
                24,
                10,
                0,
                tzinfo=dt_timezone.utc,
            ),
            action_analyzed=False,
        )

        untouched = InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            email_account=self.allowed_account,
            platform="gmail",
            direction="inbound",
            external_message_id="untouched-action-001",
            sender="other@example.com",
            recipients=self.user.email,
            subject="Contract review required",
            body="Please review the attached contract.",
            received_at=datetime(
                2026,
                8,
                24,
                10,
                0,
                tzinfo=dt_timezone.utc,
            ),
            action_analyzed=False,
        )

        processed = analyze_new_messages.run(
            message_ids=[target.id]
        )

        self.assertEqual(processed, 1)

        self.assertTrue(
            ActionItem.objects.filter(
                message=target,
            ).exists()
        )

        target.refresh_from_db()
        untouched.refresh_from_db()

        self.assertTrue(target.action_analyzed)
        self.assertFalse(untouched.action_analyzed)

        self.assertFalse(
            ActionItem.objects.filter(
                message=untouched,
            ).exists()
        )

    def test_outbound_message_is_not_action_analyzed(self):
        message = InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            email_account=self.allowed_account,
            platform="gmail",
            direction="outbound",
            external_message_id="outbound-action-001",
            sender=self.user.email,
            recipients="customer@example.com",
            subject="Quotation required",
            body="Please send the revised quotation by Friday.",
            received_at=datetime(
                2026,
                8,
                24,
                10,
                0,
                tzinfo=dt_timezone.utc,
            ),
            action_analyzed=False,
        )

        processed = analyze_new_messages.run(
            message_ids=[message.id]
        )

        self.assertEqual(processed, 0)

        self.assertFalse(
            ActionItem.objects.filter(
                message=message,
            ).exists()
        )

        message.refresh_from_db()

        self.assertFalse(
            message.action_analyzed
        )

    @patch(
        "actions.tasks."
        "extract_actions_with_ai_result"
    )
    @override_settings(
        ACTION_AI_ENABLED=True,
        ONEUCH_AI_PROVIDER="mock",
        ONEUCH_AI_MODEL="mock-model",
        ACTION_AI_AUTO_CREATE_THRESHOLD=90,
        ACTION_AI_REVIEW_THRESHOLD=75,
    )
    def test_deterministic_action_does_not_call_ai(
        self,
        ai_extract_mock,
    ):
        message = InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            email_account=self.allowed_account,
            platform="gmail",
            direction="inbound",
            external_message_id=(
                "deterministic-skips-ai-001"
            ),
            sender="customer@example.com",
            recipients=self.user.email,
            subject="Quotation required",
            body=(
                "Please send the revised "
                "quotation by Friday."
            ),
            received_at=datetime(
                2026,
                8,
                24,
                10,
                0,
                tzinfo=dt_timezone.utc,
            ),
            action_analyzed=False,
        )

        processed = analyze_new_messages.run(
            message_ids=[message.id]
        )

        self.assertEqual(
            processed,
            1,
        )

        ai_extract_mock.assert_not_called()

        action = ActionItem.objects.get(
            message=message,
        )

        self.assertEqual(
            action.source_type,
            "email",
        )


    @patch(
        "actions.tasks."
        "extract_actions_with_ai_result"
    )
    @override_settings(
        ACTION_AI_ENABLED=True,
        ONEUCH_AI_PROVIDER="mock",
        ONEUCH_AI_MODEL="mock-model",
        ACTION_AI_AUTO_CREATE_THRESHOLD=90,
        ACTION_AI_REVIEW_THRESHOLD=75,
    )
    def test_high_confidence_ai_action_is_created(
        self,
        ai_extract_mock,
    ):
        from actions.services.ai_extractor import (
            AIActionExtractionResult,
        )

        message = InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            email_account=self.allowed_account,
            platform="gmail",
            direction="inbound",
            external_message_id=(
                "ai-auto-create-001"
            ),
            sender="customer@example.com",
            recipients=self.user.email,
            subject="Deployment blocker",
            body=(
                "Can you coordinate with the "
                "infrastructure team and get "
                "the firewall access sorted?"
            ),
            received_at=datetime(
                2026,
                8,
                25,
                5,
                0,
                tzinfo=dt_timezone.utc,
            ),
            action_analyzed=False,
        )

        ai_extract_mock.return_value = (
            AIActionExtractionResult(
                success=True,
                candidates=[
                    {
                        "title": (
                            "Resolve firewall access"
                        ),
                        "description": (
                            "Coordinate with the "
                            "infrastructure team."
                        ),
                        "priority": 90,
                        "due_date": None,
                        "confidence_score": 99,
                        "owner_reference": (
                            "Abhishek"
                        ),
                        "evidence": (
                            "coordinate with the "
                            "infrastructure team"
                        ),
                        "reason": (
                            "Concrete work requested."
                        ),
                        "provider": "openai",
                        "model": "gpt-5.6-luna",
                    }
                ],
                provider="openai",
                model="gpt-5.6-luna",
            )
        )

        processed = analyze_new_messages.run(
            message_ids=[message.id]
        )

        self.assertEqual(
            processed,
            1,
        )

        action = ActionItem.objects.get(
            message=message,
        )

        self.assertEqual(
            action.title,
            "Resolve firewall access",
        )

        self.assertEqual(
            action.source_type,
            "ai",
        )

        self.assertEqual(
            action.confidence_score,
            99,
        )

        self.assertIsNone(
            action.owner
        )

        self.assertFalse(
            AIActionCandidate.objects.filter(
                message=message,
            ).exists()
        )

        message.refresh_from_db()

        self.assertTrue(
            message.action_analyzed
        )


    @patch(
        "actions.tasks."
        "extract_actions_with_ai_result"
    )
    @override_settings(
        ACTION_AI_ENABLED=True,
        ONEUCH_AI_PROVIDER="mock",
        ONEUCH_AI_MODEL="mock-model",
        ACTION_AI_AUTO_CREATE_THRESHOLD=90,
        ACTION_AI_REVIEW_THRESHOLD=75,
    )
    def test_review_confidence_creates_candidate_not_action(
        self,
        ai_extract_mock,
    ):
        from actions.services.ai_extractor import (
            AIActionExtractionResult,
        )

        message = InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            email_account=self.allowed_account,
            platform="gmail",
            direction="inbound",
            external_message_id=(
                "ai-review-001"
            ),
            sender="customer@example.com",
            recipients=self.user.email,
            subject="Commercial pending",
            body=(
                "We are still waiting on "
                "the revised commercial."
            ),
            received_at=datetime(
                2026,
                8,
                25,
                5,
                0,
                tzinfo=dt_timezone.utc,
            ),
            action_analyzed=False,
        )

        ai_extract_mock.return_value = (
            AIActionExtractionResult(
                success=True,
                candidates=[
                    {
                        "title": (
                            "Follow up on revised "
                            "commercial"
                        ),
                        "description": "",
                        "priority": 70,
                        "due_date": None,
                        "confidence_score": 82,
                        "owner_reference": "",
                        "evidence": (
                            "still waiting on the "
                            "revised commercial"
                        ),
                        "reason": (
                            "Possible outstanding work."
                        ),
                        "provider": "openai",
                        "model": "gpt-5.6-luna",
                    }
                ],
                provider="openai",
                model="gpt-5.6-luna",
            )
        )

        processed = analyze_new_messages.run(
            message_ids=[message.id]
        )

        self.assertEqual(
            processed,
            1,
        )

        self.assertFalse(
            ActionItem.objects.filter(
                message=message,
            ).exists()
        )

        candidate = (
            AIActionCandidate.objects.get(
                message=message,
            )
        )

        self.assertEqual(
            candidate.status,
            "pending_review",
        )

        self.assertEqual(
            candidate.confidence_score,
            82,
        )

        message.refresh_from_db()

        self.assertTrue(
            message.action_analyzed
        )


    @patch(
        "actions.tasks."
        "extract_actions_with_ai_result"
    )
    @override_settings(
        ACTION_AI_ENABLED=True,
        ONEUCH_AI_PROVIDER="mock",
        ONEUCH_AI_MODEL="mock-model",
        ACTION_AI_AUTO_CREATE_THRESHOLD=90,
        ACTION_AI_REVIEW_THRESHOLD=75,
    )
    def test_ai_failure_leaves_message_unanalyzed(
        self,
        ai_extract_mock,
    ):
        from actions.services.ai_extractor import (
            AIActionExtractionResult,
        )

        message = InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            email_account=self.allowed_account,
            platform="gmail",
            direction="inbound",
            external_message_id=(
                "ai-failure-001"
            ),
            sender="customer@example.com",
            recipients=self.user.email,
            subject="Customer issue",
            body=(
                "Can you get this sorted?"
            ),
            received_at=datetime(
                2026,
                8,
                25,
                5,
                0,
                tzinfo=dt_timezone.utc,
            ),
            action_analyzed=False,
        )

        ai_extract_mock.return_value = (
            AIActionExtractionResult(
                success=False,
                candidates=[],
                error="Provider unavailable",
                provider="openai",
                model="gpt-5.6-luna",
            )
        )

        processed = analyze_new_messages.run(
            message_ids=[message.id]
        )

        self.assertEqual(
            processed,
            0,
        )

        message.refresh_from_db()

        self.assertFalse(
            message.action_analyzed
        )

        self.assertFalse(
            ActionItem.objects.filter(
                message=message,
            ).exists()
        )

        self.assertFalse(
            AIActionCandidate.objects.filter(
                message=message,
            ).exists()
        )


    @patch(
        "actions.tasks."
        "extract_actions_with_ai_result"
    )
    @override_settings(
        ACTION_AI_ENABLED=True,
        ONEUCH_AI_PROVIDER="mock",
        ONEUCH_AI_MODEL="mock-model",
        ACTION_AI_AUTO_CREATE_THRESHOLD=90,
        ACTION_AI_REVIEW_THRESHOLD=75,
    )
    def test_successful_ai_no_action_marks_analyzed(
        self,
        ai_extract_mock,
    ):
        from actions.services.ai_extractor import (
            AIActionExtractionResult,
        )

        message = InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            email_account=self.allowed_account,
            platform="gmail",
            direction="inbound",
            external_message_id=(
                "ai-no-action-001"
            ),
            sender="customer@example.com",
            recipients=self.user.email,
            subject="FYI",
            body=(
                "Sharing this for your "
                "information only."
            ),
            received_at=datetime(
                2026,
                8,
                25,
                5,
                0,
                tzinfo=dt_timezone.utc,
            ),
            action_analyzed=False,
        )

        ai_extract_mock.return_value = (
            AIActionExtractionResult(
                success=True,
                candidates=[],
                provider="openai",
                model="gpt-5.6-luna",
            )
        )

        processed = analyze_new_messages.run(
            message_ids=[message.id]
        )

        self.assertEqual(
            processed,
            1,
        )

        message.refresh_from_db()

        self.assertTrue(
            message.action_analyzed
        )

        self.assertFalse(
            ActionItem.objects.filter(
                message=message,
            ).exists()
        )

    @patch(
        "actions.tasks."
        "extract_actions_with_ai_result"
    )
    @override_settings(
        ACTION_AI_ENABLED=True,
        ONEUCH_AI_PROVIDER="mock",
        ONEUCH_AI_MODEL="mock-model",
        ACTION_AI_AUTO_CREATE_THRESHOLD=90,
        ACTION_AI_REVIEW_THRESHOLD=75,
        ACTION_AI_MAX_ATTEMPTS=3,
        ACTION_AI_RETRY_BASE_SECONDS=300,
        ACTION_AI_RETRY_MAX_SECONDS=3600,
    )
    def test_ai_failure_creates_retry_state(
        self,
        ai_extract_mock,
    ):
        from actions.services.ai_extractor import (
            AIActionExtractionResult,
        )

        message = InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            email_account=self.allowed_account,
            platform="gmail",
            direction="inbound",
            external_message_id="ai-retry-001",
            sender="customer@example.com",
            recipients=self.user.email,
            subject="Customer issue",
            body="Can you get this sorted?",
            received_at=datetime(
                2026,
                8,
                25,
                5,
                0,
                tzinfo=dt_timezone.utc,
            ),
            action_analyzed=False,
        )

        ai_extract_mock.return_value = (
            AIActionExtractionResult(
                success=False,
                candidates=[],
                error="Provider unavailable",
                provider="openai",
                model="gpt-5.6-luna",
            )
        )

        processed = analyze_new_messages.run(
            message_ids=[message.id]
        )

        self.assertEqual(
            processed,
            0,
        )

        state = (
            AIActionAnalysisState.objects.get(
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

        self.assertIsNotNone(
            state.next_retry_at
        )

        message.refresh_from_db()

        self.assertFalse(
            message.action_analyzed
        )


    @patch(
        "actions.tasks."
        "extract_actions_with_ai_result"
    )
    @override_settings(
        ACTION_AI_ENABLED=True,
        ONEUCH_AI_PROVIDER="mock",
        ONEUCH_AI_MODEL="mock-model",
        ACTION_AI_AUTO_CREATE_THRESHOLD=90,
        ACTION_AI_REVIEW_THRESHOLD=75,
        ACTION_AI_MAX_ATTEMPTS=3,
        ACTION_AI_RETRY_BASE_SECONDS=300,
        ACTION_AI_RETRY_MAX_SECONDS=3600,
    )
    def test_ai_retry_wait_skips_provider_call(
        self,
        ai_extract_mock,
    ):
        from django.utils import timezone
        from datetime import timedelta

        message = InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            email_account=self.allowed_account,
            platform="gmail",
            direction="inbound",
            external_message_id="ai-retry-wait-001",
            sender="customer@example.com",
            recipients=self.user.email,
            subject="Customer issue",
            body="Can you get this sorted?",
            received_at=datetime(
                2026,
                8,
                25,
                5,
                0,
                tzinfo=dt_timezone.utc,
            ),
            action_analyzed=False,
        )

        AIActionAnalysisState.objects.create(
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

        processed = analyze_new_messages.run(
            message_ids=[message.id]
        )

        self.assertEqual(
            processed,
            0,
        )

        ai_extract_mock.assert_not_called()

        message.refresh_from_db()

        self.assertFalse(
            message.action_analyzed
        )


    @patch(
        "actions.tasks."
        "extract_actions_with_ai_result"
    )
    @override_settings(
        ACTION_AI_ENABLED=True,
        ONEUCH_AI_PROVIDER="mock",
        ONEUCH_AI_MODEL="mock-model",
        ACTION_AI_AUTO_CREATE_THRESHOLD=90,
        ACTION_AI_REVIEW_THRESHOLD=75,
        ACTION_AI_MAX_ATTEMPTS=3,
        ACTION_AI_RETRY_BASE_SECONDS=300,
        ACTION_AI_RETRY_MAX_SECONDS=3600,
    )
    def test_successful_retry_clears_retry_state(
        self,
        ai_extract_mock,
    ):
        from actions.services.ai_extractor import (
            AIActionExtractionResult,
        )

        from django.utils import timezone
        from datetime import timedelta

        message = InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            email_account=self.allowed_account,
            platform="gmail",
            direction="inbound",
            external_message_id="ai-retry-success-001",
            sender="customer@example.com",
            recipients=self.user.email,
            subject="FYI",
            body="Sharing an update.",
            received_at=datetime(
                2026,
                8,
                25,
                5,
                0,
                tzinfo=dt_timezone.utc,
            ),
            action_analyzed=False,
        )

        AIActionAnalysisState.objects.create(
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

        ai_extract_mock.return_value = (
            AIActionExtractionResult(
                success=True,
                candidates=[],
                provider="openai",
                model="gpt-5.6-luna",
            )
        )

        processed = analyze_new_messages.run(
            message_ids=[message.id]
        )

        self.assertEqual(
            processed,
            1,
        )

        self.assertFalse(
            AIActionAnalysisState.objects.filter(
                message=message,
            ).exists()
        )

        message.refresh_from_db()

        self.assertTrue(
            message.action_analyzed
        )

    @patch(
        "actions.tasks."
        "extract_actions_with_ai_result"
    )
    @override_settings(
        ACTION_AI_ENABLED=True,
        ACTION_AI_ALLOWED_ACCOUNT_IDS={1},
        ONEUCH_AI_PROVIDER="mock",
        ONEUCH_AI_MODEL="mock-model",
        ACTION_AI_AUTO_CREATE_THRESHOLD=90,
        ACTION_AI_REVIEW_THRESHOLD=75,
        ACTION_AI_MAX_ATTEMPTS=3,
        ACTION_AI_RETRY_BASE_SECONDS=300,
        ACTION_AI_RETRY_MAX_SECONDS=3600,
    )
    def test_ai_allowed_account_calls_ai(
        self,
        ai_extract_mock,
    ):
        from actions.services.ai_extractor import (
            AIActionExtractionResult,
        )

        ai_extract_mock.return_value = (
            AIActionExtractionResult(
                success=True,
                candidates=[],
                provider="mock",
                model="mock-model",
            )
        )

        message = InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            email_account=self.allowed_account,
            platform="gmail",
            direction="inbound",
            external_message_id=(
                "ai-allowed-account-001"
            ),
            sender="customer@example.com",
            recipients=self.user.email,
            subject="Customer issue",
            body="Can you get this sorted?",
            received_at=datetime(
                2026,
                8,
                25,
                5,
                0,
                tzinfo=dt_timezone.utc,
            ),
            action_analyzed=False,
        )

        with self.settings(
            ACTION_AI_ALLOWED_ACCOUNT_IDS={
                self.allowed_account.id,
            }
        ):
            processed = (
                analyze_new_messages.run(
                    message_ids=[
                        message.id
                    ]
                )
            )

        self.assertEqual(
            processed,
            1,
        )

        ai_extract_mock.assert_called_once()


    @patch(
        "actions.tasks."
        "extract_actions_with_ai_result"
    )
    @override_settings(
        ACTION_AI_ENABLED=True,
        ACTION_AI_ALLOWED_ACCOUNT_IDS={999999},
        ONEUCH_AI_PROVIDER="mock",
        ONEUCH_AI_MODEL="mock-model",
        ACTION_AI_AUTO_CREATE_THRESHOLD=90,
        ACTION_AI_REVIEW_THRESHOLD=75,
        ACTION_AI_MAX_ATTEMPTS=3,
        ACTION_AI_RETRY_BASE_SECONDS=300,
        ACTION_AI_RETRY_MAX_SECONDS=3600,
    )
    def test_non_allowed_account_does_not_call_ai(
        self,
        ai_extract_mock,
    ):
        message = InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            email_account=self.blocked_account,
            platform="gmail",
            direction="inbound",
            external_message_id=(
                "ai-blocked-account-001"
            ),
            sender="customer@example.com",
            recipients=self.user.email,
            subject="Customer issue",
            body="Can you get this sorted?",
            received_at=datetime(
                2026,
                8,
                25,
                5,
                0,
                tzinfo=dt_timezone.utc,
            ),
            action_analyzed=False,
        )

        processed = analyze_new_messages.run(
            message_ids=[
                message.id
            ]
        )

        self.assertEqual(
            processed,
            1,
        )

        ai_extract_mock.assert_not_called()

        message.refresh_from_db()

        self.assertTrue(
            message.action_analyzed
        )

