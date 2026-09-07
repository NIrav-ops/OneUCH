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

from inbox.models import (
    Organization,
    OrganizationUser,
)

from inbox.tasks import (
    sync_email_account,
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

        self.organization = (
            Organization.objects.create(
                name=(
                    "Periodic IMAP Test Organization"
                ),
                slug=(
                    "periodic-imap-test-organization"
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

    def create_account(
        self,
        *,
        password,
    ):
        return (
            EmailAccount.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
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
                credential_status="active",
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

        lock = Mock()

        acquire_sync_lock.return_value = (
            lock
        )

        sync_email_account.run(account.id)

        fetch_imap_emails.assert_called_once_with(
            user=self.user,
            email_account=account,
            password=(
                "temporary-app-password"
            ),
        )

        # Provider mock created no InboxMessage rows.
        # C5D therefore has no mailbox-scoped intelligence work.
        analyze_approvals.assert_not_called()

        # Lock-release correctness is a separate
        # MVP-07.3A concern. This test only proves
        # the IMAP credential contract.
        release_sync_lock.assert_called_once_with(
            lock
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
    def test_periodic_imap_sync_skips_account_without_app_password(
        self,
        acquire_sync_lock,
        fetch_imap_emails,
        analyze_approvals,
        release_sync_lock,
    ):
        account = self.create_account(
            password=None,
        )

        lock = Mock()

        acquire_sync_lock.return_value = (
            lock
        )

        sync_email_account.run(account.id)

        fetch_imap_emails.assert_not_called()

        analyze_approvals.assert_not_called()

        release_sync_lock.assert_called_once_with(
            lock
        )
