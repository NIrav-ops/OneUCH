from unittest.mock import Mock, patch
from uuid import uuid4

from django.test import TestCase

from accounts.models import User
from email_accounts.models import EmailAccount
from email_accounts.services.imap_convergence import (
    IMAPConvergenceError,
)
from inbox.models import (
    Organization,
    OrganizationUser,
)
from inbox.tasks import sync_email_account


class MailConvergenceResilienceTests(
    TestCase
):

    def setUp(self):
        self.user = User.objects.create_user(
            email=(
                "mail-resilience-"
                + uuid4().hex
                + "@oneuch.test"
            ),
            password="Synthetic-Test-Password",
        )

        self.organization = (
            Organization.objects.create(
                name="Mail Resilience",
                slug=(
                    "mail-resilience-"
                    + uuid4().hex
                ),
            )
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=self.organization,
            role="owner",
        )

        self.account = (
            EmailAccount.objects.create(
                user=self.user,
                organization=self.organization,
                account_type="imap",
                email_address=(
                    "resilience@example.com"
                ),
                imap_server="imap.example.com",
                imap_port=993,
                smtp_server="smtp.example.com",
                smtp_port=465,
                smtp_password=(
                    "Synthetic-Test-Credential"
                ),
                credential_status="active",
                is_active=True,
            )
        )


    def test_trash_reconciliation_failure_does_not_fail_mail_sync(
        self,
    ):
        lock = Mock()

        handoff = {
            "message_count": 0,
            "batch_count": 0,
        }

        with (
            patch(
                "inbox.tasks.acquire_sync_lock",
                return_value=lock,
            ) as acquire_mock,
            patch(
                "inbox.tasks.release_sync_lock",
            ) as release_mock,
            patch(
                "inbox.tasks.fetch_imap_emails",
            ) as fetch_mock,
            patch(
                "inbox.tasks.reconcile_imap_trash",
                side_effect=(
                    IMAPConvergenceError(
                        "Synthetic reconciliation failure."
                    )
                ),
            ) as reconcile_mock,
            patch(
                (
                    "inbox.tasks."
                    "_queue_scoped_mail_intelligence"
                ),
                return_value=handoff,
            ) as handoff_mock,
            patch(
                (
                    "inbox.tasks."
                    "_broadcast_inbox_sync_event"
                ),
            ) as broadcast_mock,
        ):
            result = (
                sync_email_account.run(
                    self.account.id
                )
            )

        self.assertEqual(
            result["status"],
            "completed",
        )

        acquire_mock.assert_called_once_with(
            self.account.id,
            timeout=7200,
        )

        fetch_mock.assert_called_once()

        reconcile_mock.assert_called_once_with(
            user=self.user,
            email_account=self.account,
        )

        handoff_mock.assert_called_once_with(
            account=self.account,
        )

        broadcast_mock.assert_called_once_with(
            account=self.account,
            event="sync_completed",
        )

        release_mock.assert_called_once_with(
            lock
        )
