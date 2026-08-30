from unittest.mock import (
    Mock,
    patch,
)

from django.contrib.auth import (
    get_user_model,
)

from django.test import (
    TestCase,
)

from email_accounts.models import (
    EmailAccount,
)

from inbox.tasks import (
    periodic_sync_all_users,
)


User = get_user_model()


class PeriodicIMAPSyncTests(
    TestCase
):

    def setUp(self):
        self.user = (
            User.objects.create_user(
                email="imap-pilot@oneuch.test",
                password="pass123",
            )
        )

    def create_account(
        self,
        *,
        password,
    ):
        return (
            EmailAccount.objects.create(
                user=self.user,
                account_type="imap",
                email_address=(
                    "imap-pilot@example.com"
                ),
                imap_server=(
                    "imap.example.com"
                ),
                imap_port=993,
                smtp_server=(
                    "smtp.example.com"
                ),
                smtp_port=465,
                smtp_password=password,
                is_active=True,
            )
        )

    @patch(
        "inbox.tasks.release_sync_lock"
    )
    @patch(
        "inbox.tasks.analyze_new_approvals.delay"
    )
    @patch(
        "inbox.tasks.fetch_imap_emails"
    )
    @patch(
        "inbox.tasks.acquire_sync_lock"
    )
    def test_periodic_imap_sync_uses_existing_app_password(
        self,
        acquire_sync_lock,
        fetch_imap_emails,
        analyze_approvals,
        release_sync_lock,
    ):
        account = self.create_account(
            password="temporary-app-password",
        )

        acquire_sync_lock.return_value = (
            Mock()
        )

        periodic_sync_all_users.run()

        fetch_imap_emails.assert_called_once_with(
            user=self.user,
            email_account=account,
            password=(
                "temporary-app-password"
            ),
        )

        analyze_approvals.assert_called_once()

        # Lock-release correctness is a separate
        # MVP-07.3A concern. This test only proves
        # the IMAP credential contract.
        release_sync_lock.assert_called_once()

    @patch(
        "inbox.tasks.release_sync_lock"
    )
    @patch(
        "inbox.tasks.analyze_new_approvals.delay"
    )
    @patch(
        "inbox.tasks.fetch_imap_emails"
    )
    @patch(
        "inbox.tasks.acquire_sync_lock"
    )
    def test_periodic_imap_sync_skips_account_without_app_password(
        self,
        acquire_sync_lock,
        fetch_imap_emails,
        analyze_approvals,
        release_sync_lock,
    ):
        self.create_account(
            password=None,
        )

        acquire_sync_lock.return_value = (
            Mock()
        )

        periodic_sync_all_users.run()

        fetch_imap_emails.assert_not_called()

        analyze_approvals.assert_not_called()

        release_sync_lock.assert_called_once()
