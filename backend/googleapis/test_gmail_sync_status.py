from datetime import (
    timedelta,
)

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

from django.utils import (
    timezone,
)

from email_accounts.models import (
    EmailAccount,
)

from inbox.models import (
    InboxSyncStatus,
)

from oauth_tokens.models import (
    OAuthToken,
)

from googleapis.services.gmail_sync import (
    _fetch_gmail_emails_impl,
    fetch_gmail_emails,
)


User = get_user_model()


class GmailScheduledSyncStatusTests(
    TestCase
):

    def setUp(self):
        self.user = (
            User.objects.create_user(
                email=(
                    "gmail-sync-status@oneuch.test"
                ),
                password="pass123",
            )
        )

        self.account = (
            EmailAccount.objects.create(
                user=self.user,
                account_type="gmail",
                email_address=(
                    "gmail-sync-status@gmail.com"
                ),
                is_active=True,
            )
        )

    @patch(
        "googleapis.services.gmail_sync."
        "_fetch_gmail_emails_impl"
    )
    @patch(
        "googleapis.services.gmail_sync."
        "update_sync_status"
    )
    def test_marks_syncing_then_success(
        self,
        update_status,
        sync_impl,
    ):
        sync_impl.return_value = None

        fetch_gmail_emails(
            user=self.user,
            email_account=self.account,
        )

        self.assertEqual(
            update_status.call_args_list,
            [
                call(
                    user=self.user,
                    platform="gmail",
                    status="syncing",
                    progress=0,
                    error_message="",
                ),
                call(
                    user=self.user,
                    platform="gmail",
                    status="success",
                    progress=100,
                    error_message="",
                ),
            ],
        )

    @patch(
        "googleapis.services.gmail_sync."
        "_fetch_gmail_emails_impl"
    )
    @patch(
        "googleapis.services.gmail_sync."
        "update_sync_status"
    )
    def test_marks_failed_and_propagates_error(
        self,
        update_status,
        sync_impl,
    ):
        sync_impl.side_effect = RuntimeError(
            "Gmail provider unavailable"
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "Gmail provider unavailable",
        ):
            fetch_gmail_emails(
                user=self.user,
                email_account=self.account,
            )

        self.assertEqual(
            update_status.call_args_list,
            [
                call(
                    user=self.user,
                    platform="gmail",
                    status="syncing",
                    progress=0,
                    error_message="",
                ),
                call(
                    user=self.user,
                    platform="gmail",
                    status="failed",
                    progress=0,
                    error_message=(
                        "Gmail provider unavailable"
                    ),
                ),
            ],
        )

    @patch(
        "googleapis.services.gmail_sync."
        "_fetch_gmail_emails_impl"
    )
    def test_success_persists_sync_health_and_timestamp(
        self,
        sync_impl,
    ):
        sync_impl.return_value = None

        fetch_gmail_emails(
            user=self.user,
            email_account=self.account,
        )

        sync = (
            InboxSyncStatus.objects.get(
                user=self.user,
                platform="gmail",
            )
        )

        self.assertEqual(
            sync.status,
            "success",
        )

        self.assertEqual(
            sync.progress,
            100,
        )

        self.assertEqual(
            sync.error_message,
            "",
        )

        self.assertIsNotNone(
            sync.last_synced_at
        )

    @patch(
        "googleapis.services.gmail_sync.build"
    )
    def test_scheduled_impl_respects_admin_disabled_policy(
        self,
        build,
    ):
        OAuthToken.objects.create(
            user=self.user,
            provider="google",
            access_token="access-token",
            refresh_token="refresh-token",
            expires_at=(
                timezone.now()
                + timedelta(hours=1)
            ),
            is_active=True,
            disabled_by_admin=True,
        )

        with self.assertRaisesRegex(
            Exception,
            "disabled by administrator",
        ):
            _fetch_gmail_emails_impl(
                user=self.user,
                email_account=self.account,
            )

        build.assert_not_called()

    def test_partial_thread_failure_attempts_remaining_threads(
        self,
    ):
        from inbox.models import (
            InboxMessage,
            Organization,
            OrganizationUser,
        )

        organization = (
            Organization.objects.create(
                name="Gmail Partial Sync Org",
                slug="gmail-partial-sync-org",
            )
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=organization,
            role="member",
        )

        service = Mock()

        threads_api = (
            service
            .users.return_value
            .threads.return_value
        )

        threads_api.list.return_value.execute.return_value = {
            "threads": [
                {
                    "id": "failed-thread",
                },
                {
                    "id": "healthy-thread",
                },
            ],
        }

        healthy_message = {
            "id":
                "healthy-message",

            "threadId":
                "healthy-thread",

            "labelIds": [
                "INBOX",
            ],

            "snippet":
                "Healthy message body",

            "internalDate":
                "1788076800000",

            "payload": {
                "headers": [
                    {
                        "name":
                            "Subject",

                        "value":
                            "Healthy Gmail message",
                    },
                    {
                        "name":
                            "From",

                        "value":
                            "customer@example.com",
                    },
                    {
                        "name":
                            "To",

                        "value":
                            self.account.email_address,
                    },
                ],
            },
        }

        def resolve_thread(
            *,
            userId,
            id,
        ):
            operation = Mock()

            if id == "failed-thread":
                operation.execute.side_effect = (
                    RuntimeError(
                        "individual thread unavailable"
                    )
                )

            elif id == "healthy-thread":
                operation.execute.return_value = {
                    "messages": [
                        healthy_message,
                    ],
                }

            else:
                raise AssertionError(
                    f"Unexpected Gmail thread: {id}"
                )

            return operation

        threads_api.get.side_effect = (
            resolve_thread
        )

        channel_layer = Mock()

        with (
            patch(
                "googleapis.services.gmail_sync."
                "get_gmail_credentials",
                return_value=Mock(),
            ),
            patch(
                "googleapis.services.gmail_sync."
                "build",
                return_value=service,
            ),
            patch(
                "googleapis.services.gmail_sync."
                "MessageProcessor"
            ),
            patch(
                "googleapis.services.gmail_sync."
                "invalidate_conversation_cache"
            ),
            patch(
                "googleapis.services.gmail_sync."
                "get_channel_layer",
                return_value=channel_layer,
            ),
            patch(
                "googleapis.services.gmail_sync."
                "async_to_sync"
            ) as async_to_sync,
        ):
            async_to_sync.return_value = (
                Mock()
            )

            with self.assertRaisesRegex(
                RuntimeError,
                (
                    "Gmail partial sync failure: "
                    r"1 thread\(s\) failed"
                ),
            ):
                fetch_gmail_emails(
                    user=self.user,
                    email_account=self.account,
                )

        # Failure in the first thread must not abort the
        # remaining mailbox traversal.
        self.assertEqual(
            [
                item.kwargs["id"]
                for item
                in threads_api.get.call_args_list
            ],
            [
                "failed-thread",
                "healthy-thread",
            ],
        )

        # Successful mail from a later thread remains persisted.
        healthy = (
            InboxMessage.objects.get(
                email_account=self.account,
                external_message_id=(
                    "healthy-message"
                ),
            )
        )

        self.assertEqual(
            healthy.subject,
            "Healthy Gmail message",
        )

        self.assertEqual(
            healthy.direction,
            "inbound",
        )

        # But operational truth must report an incomplete sync.
        sync = (
            InboxSyncStatus.objects.get(
                user=self.user,
                platform="gmail",
            )
        )

        self.assertEqual(
            sync.status,
            "failed",
        )

        self.assertEqual(
            sync.progress,
            0,
        )

        self.assertIn(
            "1 thread(s) failed",
            sync.error_message,
        )

        self.assertIsNone(
            sync.last_synced_at
        )
