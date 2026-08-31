from datetime import (
    timedelta,
)

from django.contrib.auth import (
    get_user_model,
)

from django.test import (
    TestCase,
)

from django.utils import (
    timezone,
)

from email_accounts.models import (
    EmailAccount,
)

from inbox.models import (
    Conversation,
    InboxMessage,
    Organization,
    OrganizationUser,
)

from inbox.services.mail_sync_policy import (
    INITIAL_HISTORY_DAYS,
    INCREMENTAL_OVERLAP_DAYS,
    mark_initial_history_complete,
    resolve_mail_sync_window,
)


User = get_user_model()


class MailSyncPolicyTests(
    TestCase
):

    def setUp(
        self,
    ):

        self.user = (
            User.objects.create_user(
                email=(
                    "mail-policy@oneuch.test"
                ),
                password="pass123",
            )
        )

        self.organization = (
            Organization.objects.create(
                name=(
                    "Mail Policy Org"
                ),
                slug=(
                    "mail-policy-org"
                ),
            )
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=(
                self.organization
            ),
            role="member",
        )

        self.account = (
            EmailAccount.objects.create(
                user=self.user,
                account_type="gmail",
                email_address=(
                    "mail-policy@gmail.com"
                ),
                is_active=True,
            )
        )


    def test_initial_window_is_exactly_ninety_days(
        self,
    ):

        now = timezone.now()

        window = (
            resolve_mail_sync_window(
                email_account=(
                    self.account
                ),
                now=now,
            )
        )

        self.assertTrue(
            window.initial_history
        )

        self.assertEqual(
            window.cutoff,
            (
                now
                - timedelta(
                    days=(
                        INITIAL_HISTORY_DAYS
                    )
                )
            ),
        )


    def test_initial_history_completion_is_persisted_once(
        self,
    ):

        completed = timezone.now()

        self.assertTrue(
            mark_initial_history_complete(
                email_account=(
                    self.account
                ),
                completed_at=completed,
            )
        )

        self.account.refresh_from_db()

        self.assertEqual(
            self.account
            .history_sync_completed_at,
            completed,
        )

        later = (
            completed
            + timedelta(hours=1)
        )

        self.assertFalse(
            mark_initial_history_complete(
                email_account=(
                    self.account
                ),
                completed_at=later,
            )
        )

        self.account.refresh_from_db()

        self.assertEqual(
            self.account
            .history_sync_completed_at,
            completed,
        )


    def test_incremental_window_uses_latest_message_with_overlap(
        self,
    ):

        history_completed = (
            timezone.now()
            - timedelta(days=10)
        )

        self.account.history_sync_completed_at = (
            history_completed
        )

        self.account.save(
            update_fields=[
                "history_sync_completed_at",
            ]
        )


        latest_at = (
            timezone.now()
            - timedelta(hours=2)
        )


        conversation = (
            Conversation.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                email_account=(
                    self.account
                ),
                conversation_key=(
                    "gmail-policy-thread"
                ),
                subject="Policy",
            )
        )


        InboxMessage.objects.create(
            user=self.user,
            organization=(
                self.organization
            ),
            email_account=(
                self.account
            ),
            conversation=(
                conversation
            ),
            platform="gmail",
            direction="inbound",
            external_message_id=(
                "policy-message"
            ),
            external_conversation_id=(
                "policy-thread"
            ),
            sender=(
                "sender@example.com"
            ),
            recipients=(
                self.account.email_address
            ),
            subject="Policy",
            body="Body",
            received_at=(
                latest_at
            ),
        )


        window = (
            resolve_mail_sync_window(
                email_account=(
                    self.account
                ),
            )
        )


        self.assertFalse(
            window.initial_history
        )

        self.assertEqual(
            window.cutoff,
            (
                latest_at
                - timedelta(
                    days=(
                        INCREMENTAL_OVERLAP_DAYS
                    )
                )
            ),
        )


    def test_empty_completed_mailbox_uses_completion_time(
        self,
    ):

        completed = (
            timezone.now()
            - timedelta(hours=4)
        )

        self.account.history_sync_completed_at = (
            completed
        )

        self.account.save(
            update_fields=[
                "history_sync_completed_at",
            ]
        )


        window = (
            resolve_mail_sync_window(
                email_account=(
                    self.account
                ),
            )
        )


        self.assertFalse(
            window.initial_history
        )

        self.assertEqual(
            window.cutoff,
            (
                completed
                - timedelta(
                    days=(
                        INCREMENTAL_OVERLAP_DAYS
                    )
                )
            ),
        )
