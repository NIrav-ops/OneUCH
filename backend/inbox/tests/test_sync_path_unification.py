from unittest.mock import (
    Mock,
    call,
    patch,
)

from django.contrib.auth import (
    get_user_model,
)

from django.test import (
    TestCase,
)

from rest_framework.test import (
    APIClient,
)

from email_accounts.models import (
    EmailAccount,
)

from inbox.models import (
    Organization,
    OrganizationUser,
)

from inbox.tasks import (
    periodic_sync_all_users,
    sync_email_account,
)


User = get_user_model()


class SyncPathUnificationTests(
    TestCase
):

    def setUp(
        self,
    ):

        self.client = (
            APIClient()
        )


        self.user = (
            User.objects.create_user(
                email=(
                    "sync-unification@oneuch.test"
                ),
                password="pass123",
            )
        )


        self.organization = (
            Organization.objects.create(
                name=(
                    "Sync Unification Org"
                ),
                slug=(
                    "sync-unification-org"
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


        self.client.force_authenticate(
            user=self.user
        )


    def account(
        self,
        account_type,
    ):

        domain = (
            "gmail.com"
            if account_type == "gmail"
            else "contoso.example"
        )


        return (
            EmailAccount.objects.create(
                user=self.user,
                account_type=(
                    account_type
                ),
                email_address=(
                    f"{account_type}@{domain}"
                ),
                credential_status="active",
                is_active=True,
            )
        )


    @patch(
        "inbox.tasks."
        "sync_email_account.delay"
    )
    def test_manual_gmail_sync_queues_governed_account_task(
        self,
        queue_sync,
    ):

        account = (
            self.account(
                "gmail"
            )
        )


        response = (
            self.client.post(
                "/api/google/oauth/sync/",
                {},
                format="json",
            )
        )


        self.assertEqual(
            response.status_code,
            202,
        )


        self.assertEqual(
            response.data[
                "status"
            ],
            "sync_queued",
        )


        self.assertEqual(
            response.data[
                "provider"
            ],
            "gmail",
        )


        queue_sync.assert_called_once_with(
            account.id
        )


    @patch(
        "inbox.tasks."
        "sync_email_account.delay"
    )
    def test_manual_outlook_sync_queues_same_governed_account_task(
        self,
        queue_sync,
    ):

        account = (
            self.account(
                "outlook"
            )
        )


        response = (
            self.client.post(
                (
                    "/api/microsoft/"
                    "oauth/sync/"
                ),
                {},
                format="json",
            )
        )


        self.assertEqual(
            response.status_code,
            202,
        )


        self.assertEqual(
            response.data[
                "status"
            ],
            "sync_queued",
        )


        self.assertEqual(
            response.data[
                "provider"
            ],
            "outlook",
        )


        queue_sync.assert_called_once_with(
            account.id
        )


    @patch(
        "inbox.tasks."
        "sync_email_account.delay"
    )
    def test_manual_queue_failure_does_not_expose_raw_broker_error(
        self,
        queue_sync,
    ):

        self.account(
            "gmail"
        )


        queue_sync.side_effect = (
            RuntimeError(
                (
                    "redis://"
                    "private-host:"
                    "6379/0"
                )
            )
        )


        response = (
            self.client.post(
                "/api/google/oauth/sync/",
                {},
                format="json",
            )
        )


        self.assertEqual(
            response.status_code,
            503,
        )


        self.assertEqual(
            response.data[
                "status"
            ],
            "queue_failed",
        )


        self.assertNotIn(
            "private-host",
            str(
                response.data
            ),
        )


    @patch(
        "inbox.tasks."
        "sync_email_account.delay"
    )
    def test_scheduler_fans_out_through_same_account_task(
        self,
        queue_sync,
    ):

        gmail = (
            self.account(
                "gmail"
            )
        )

        outlook = (
            self.account(
                "outlook"
            )
        )


        result = (
            periodic_sync_all_users.run()
        )


        self.assertEqual(
            result[
                "queued"
            ],
            2,
        )


        self.assertEqual(
            result[
                "failed"
            ],
            0,
        )


        self.assertEqual(
            queue_sync.call_count,
            2,
        )


        self.assertCountEqual(
            [
                item.args[0]
                for item
                in queue_sync.call_args_list
            ],
            [
                gmail.id,
                outlook.id,
            ],
        )


    @patch(
        "inbox.tasks."
        "release_sync_lock"
    )
    @patch(
        "inbox.tasks."
        "analyze_new_approvals.delay"
    )
    @patch(
        "inbox.tasks."
        "fetch_gmail_emails"
    )
    @patch(
        "inbox.tasks."
        "acquire_sync_lock"
    )
    def test_governed_account_task_uses_p1a_gmail_core(
        self,
        acquire_lock,
        gmail_core,
        analyze,
        release_lock,
    ):

        account = (
            self.account(
                "gmail"
            )
        )


        lock = Mock()

        acquire_lock.return_value = (
            lock
        )


        result = (
            sync_email_account.run(
                account.id
            )
        )


        self.assertEqual(
            result[
                "status"
            ],
            "completed",
        )


        gmail_core.assert_called_once_with(
            user=self.user,
            email_account=(
                account
            ),
        )


        analyze.assert_called_once()

        release_lock.assert_called_once_with(
            lock
        )


    @patch(
        "inbox.tasks."
        "release_sync_lock"
    )
    @patch(
        "inbox.tasks."
        "analyze_new_approvals.delay"
    )
    @patch(
        "inbox.tasks."
        "fetch_outlook_emails"
    )
    @patch(
        "inbox.tasks."
        "acquire_sync_lock"
    )
    def test_governed_account_task_uses_p1b_outlook_core(
        self,
        acquire_lock,
        outlook_core,
        analyze,
        release_lock,
    ):

        account = (
            self.account(
                "outlook"
            )
        )


        lock = Mock()

        acquire_lock.return_value = (
            lock
        )


        result = (
            sync_email_account.run(
                account.id
            )
        )


        self.assertEqual(
            result[
                "status"
            ],
            "completed",
        )


        outlook_core.assert_called_once_with(
            user=self.user,
            email_account=(
                account
            ),
        )


        analyze.assert_called_once()

        release_lock.assert_called_once_with(
            lock
        )


    @patch(
        "inbox.tasks."
        "release_sync_lock"
    )
    @patch(
        "inbox.tasks."
        "fetch_gmail_emails"
    )
    @patch(
        "inbox.tasks."
        "acquire_sync_lock"
    )
    def test_provider_failure_releases_mailbox_lock_and_remains_failed(
        self,
        acquire_lock,
        gmail_core,
        release_lock,
    ):

        account = (
            self.account(
                "gmail"
            )
        )


        lock = Mock()

        acquire_lock.return_value = (
            lock
        )


        gmail_core.side_effect = (
            RuntimeError(
                "provider failure"
            )
        )


        with self.assertRaisesRegex(
            RuntimeError,
            "provider failure",
        ):

            sync_email_account.run(
                account.id
            )


        release_lock.assert_called_once_with(
            lock
        )


    @patch(
        "inbox.tasks."
        "release_sync_lock"
    )
    @patch(
        "inbox.tasks."
        "fetch_gmail_emails"
    )
    @patch(
        "inbox.tasks."
        "acquire_sync_lock"
    )
    def test_existing_sync_lock_prevents_duplicate_mailbox_execution(
        self,
        acquire_lock,
        gmail_core,
        release_lock,
    ):

        account = (
            self.account(
                "gmail"
            )
        )


        acquire_lock.return_value = (
            None
        )


        result = (
            sync_email_account.run(
                account.id
            )
        )


        self.assertEqual(
            result[
                "reason"
            ],
            "already_syncing",
        )


        gmail_core.assert_not_called()

        release_lock.assert_not_called()
