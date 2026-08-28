from datetime import (
    datetime,
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

from approvals.models import (
    ApprovalItem,
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


class ApprovalAIGovernanceModeTests(
    TestCase
):

    def setUp(self):
        self.user = User.objects.create_user(
            email="approval-governance@test.com",
            password="pass123",
        )

        self.organization = (
            Organization.objects.create(
                name="Approval Governance Test",
                slug="approval-governance-test",
            )
        )

        self.account = (
            EmailAccount.objects.create(
                user=self.user,
                account_type="gmail",
                email_address=(
                    "approval-governance@test.com"
                ),
                is_active=True,
            )
        )

    @patch(
        "approvals.tasks."
        "extract_approvals_with_ai_result"
    )
    @override_settings(
        APPROVAL_AI_ENABLED=True,
        ONEUCH_AI_MODE="deterministic_only",
        ONEUCH_AI_PROVIDER="openai",
        ONEUCH_AI_MODEL="test-model",
    )
    def test_deterministic_only_skips_semantic_ai(
        self,
        ai_mock,
    ):
        message = InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            email_account=self.account,
            platform="gmail",
            direction="inbound",
            external_message_id=(
                "approval-governance-001"
            ),
            sender="customer@example.com",
            recipients=self.user.email,
            subject="Information",
            body=(
                "Sharing this deployment update "
                "for information only."
            ),
            received_at=datetime(
                2026,
                8,
                28,
                0,
                0,
                tzinfo=dt_timezone.utc,
            ),
            approval_analyzed=False,
        )

        with self.settings(
            APPROVAL_AI_ALLOWED_ACCOUNT_IDS={
                self.account.id,
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
