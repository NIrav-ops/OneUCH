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

from actions.models import (
    ActionItem,
)
from actions.tasks import (
    analyze_new_messages,
)
from email_accounts.models import (
    EmailAccount,
)
from inbox.models import (
    InboxMessage,
    Organization,
)


User = get_user_model()


class ActionAIGovernanceModeTests(
    TestCase
):

    def setUp(self):
        self.user = User.objects.create_user(
            email="action-governance@test.com",
            password="pass123",
        )

        self.organization = (
            Organization.objects.create(
                name="Action Governance Test",
                slug="action-governance-test",
            )
        )

        self.account = (
            EmailAccount.objects.create(
                user=self.user,
                account_type="gmail",
                email_address=(
                    "action-governance@test.com"
                ),
                is_active=True,
            )
        )

    @patch(
        "actions.tasks."
        "extract_actions_with_ai_result"
    )
    @override_settings(
        ACTION_AI_ENABLED=True,
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
                "action-governance-001"
            ),
            sender="customer@example.com",
            recipients=self.user.email,
            subject="Information",
            body=(
                "Sharing this update for "
                "your information only."
            ),
            received_at=datetime(
                2026,
                8,
                28,
                0,
                0,
                tzinfo=dt_timezone.utc,
            ),
            action_analyzed=False,
        )

        with self.settings(
            ACTION_AI_ALLOWED_ACCOUNT_IDS={
                self.account.id,
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

        ai_mock.assert_not_called()

        message.refresh_from_db()

        self.assertTrue(
            message.action_analyzed
        )

        self.assertFalse(
            ActionItem.objects.filter(
                message=message,
            ).exists()
        )
