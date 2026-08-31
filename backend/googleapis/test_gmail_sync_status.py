import base64

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

    def test_partial_message_failure_attempts_remaining_messages(
        self,
    ):
        from inbox.models import (
            InboxMessage,
            Organization,
            OrganizationUser,
        )


        organization = (
            Organization.objects.create(
                name=(
                    "Gmail Partial Sync Org"
                ),
                slug=(
                    "gmail-partial-sync-org"
                ),
            )
        )


        OrganizationUser.objects.create(
            user=self.user,
            organization=organization,
            role="member",
        )


        service = Mock()


        messages_api = (
            service
            .users.return_value
            .messages.return_value
        )


        list_operation = Mock()

        list_operation.execute.return_value = {
            "messages": [
                {
                    "id":
                        "failed-message",
                },
                {
                    "id":
                        "healthy-message",
                },
            ],
        }


        messages_api.list.return_value = (
            list_operation
        )


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
                "mimeType":
                    "text/plain",

                "headers": [
                    {
                        "name":
                            "Subject",

                        "value":
                            (
                                "Healthy "
                                "Gmail message"
                            ),
                    },
                    {
                        "name":
                            "From",

                        "value":
                            (
                                "Customer "
                                "<customer@example.com>"
                            ),
                    },
                    {
                        "name":
                            "To",

                        "value":
                            (
                                self.account
                                .email_address
                            ),
                    },
                ],

                # Deliberately omit body data here.
                # The ingestion contract may safely
                # fall back to Gmail snippet when the
                # provider payload contains no usable
                # text body.
                "body": {},
            },
        }


        def resolve_message(
            *,
            userId,
            id,
            format,
        ):

            self.assertEqual(
                userId,
                "me",
            )

            self.assertEqual(
                format,
                "full",
            )


            operation = Mock()


            if id == "failed-message":

                operation.execute.side_effect = (
                    RuntimeError(
                        (
                            "individual message "
                            "unavailable"
                        )
                    )
                )


            elif id == "healthy-message":

                operation.execute.return_value = (
                    healthy_message
                )


            else:

                raise AssertionError(
                    (
                        "Unexpected Gmail "
                        f"message: {id}"
                    )
                )


            return operation


        messages_api.get.side_effect = (
            resolve_message
        )


        channel_layer = Mock()


        with (
            patch(
                (
                    "googleapis.services."
                    "gmail_sync."
                    "get_gmail_credentials"
                ),
                return_value=Mock(),
            ),
            patch(
                (
                    "googleapis.services."
                    "gmail_sync.build"
                ),
                return_value=service,
            ),
            patch(
                (
                    "googleapis.services."
                    "gmail_sync."
                    "MessageProcessor"
                )
            ),
            patch(
                (
                    "googleapis.services."
                    "gmail_sync."
                    "invalidate_conversation_cache"
                )
            ),
            patch(
                (
                    "googleapis.services."
                    "gmail_sync."
                    "get_channel_layer"
                ),
                return_value=channel_layer,
            ),
            patch(
                (
                    "googleapis.services."
                    "gmail_sync."
                    "async_to_sync"
                )
            ) as async_to_sync,
        ):

            async_to_sync.return_value = (
                Mock()
            )


            with self.assertRaisesRegex(
                RuntimeError,
                (
                    "Gmail partial sync failure: "
                    r"1 message\(s\) failed"
                ),
            ):

                fetch_gmail_emails(
                    user=self.user,
                    email_account=(
                        self.account
                    ),
                )


        # Failure in one provider message must not
        # abort traversal of the remaining messages.
        self.assertEqual(
            [
                item.kwargs["id"]
                for item
                in messages_api
                .get.call_args_list
            ],
            [
                "failed-message",
                "healthy-message",
            ],
        )


        # Healthy mail later in the same provider
        # traversal must still be persisted.
        healthy = (
            InboxMessage.objects.get(
                email_account=(
                    self.account
                ),
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


        self.assertEqual(
            healthy.folder,
            "inbox",
        )


        self.assertEqual(
            healthy.body,
            "Healthy message body",
        )


        self.assertEqual(
            healthy.sender,
            "customer@example.com",
        )


        # Operational truth must report that the
        # provider traversal was incomplete.
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
            "1 message(s) failed",
            sync.error_message,
        )


        self.assertIsNone(
            sync.last_synced_at
        )


        # A partial initial import must remain
        # retryable and must never be marked complete.
        self.account.refresh_from_db()


        self.assertIsNone(
            self.account
            .history_sync_completed_at
        )


        # Historical initial backfill deliberately
        # suppresses per-message WebSocket events.
        async_to_sync.assert_not_called()

class GmailHistoryCorrectnessTests(
    TestCase
):

    def setUp(
        self,
    ):

        from inbox.models import (
            Organization,
            OrganizationUser,
        )


        self.user = (
            User.objects.create_user(
                email=(
                    "gmail-history@oneuch.test"
                ),
                password="pass123",
            )
        )


        self.organization = (
            Organization.objects.create(
                name=(
                    "Gmail History Org"
                ),
                slug=(
                    "gmail-history-org"
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
                    "pilot@gmail.com"
                ),
                is_active=True,
            )
        )


    def encoded(
        self,
        value,
    ):

        return (
            base64
            .urlsafe_b64encode(
                value.encode(
                    "utf-8"
                )
            )
            .decode(
                "ascii"
            )
            .rstrip("=")
        )


    def gmail_message(
        self,
        *,
        message_id,
        thread_id,
        body,
        internal_date,
        labels=None,
    ):

        return {
            "id":
                message_id,

            "threadId":
                thread_id,

            "labelIds":
                (
                    labels
                    or [
                        "INBOX",
                        "UNREAD",
                    ]
                ),

            "snippet":
                "This is only the preview.",

            "internalDate":
                internal_date,

            "payload": {
                "mimeType":
                    "text/plain",

                "headers": [
                    {
                        "name":
                            "Subject",

                        "value":
                            "Full body requirement",
                    },
                    {
                        "name":
                            "From",

                        "value":
                            (
                                "Customer Name "
                                "<customer@example.com>"
                            ),
                    },
                    {
                        "name":
                            "To",

                        "value":
                            (
                                "Pilot User "
                                "<pilot@gmail.com>"
                            ),
                    },
                    {
                        "name":
                            "Cc",

                        "value":
                            (
                                "Finance Team "
                                "<finance@example.com>"
                            ),
                    },
                    {
                        "name":
                            "Bcc",

                        "value":
                            (
                                "Audit Team "
                                "<audit@example.com>"
                            ),
                    },
                    {
                        "name":
                            "Reply-To",

                        "value":
                            (
                                "Support "
                                "<support@example.com>"
                            ),
                    },
                    {
                        "name":
                            "Content-Type",

                        "value":
                            (
                                "text/plain; "
                                "charset=utf-8"
                            ),
                    },
                ],

                "body": {
                    "data":
                        self.encoded(
                            body
                        ),
                },
            },
        }


    def run_provider(
        self,
        *,
        pages,
        messages,
    ):

        service = Mock()

        messages_api = (
            service
            .users.return_value
            .messages.return_value
        )


        page_operations = []

        for page in pages:

            operation = Mock()

            operation.execute.return_value = (
                page
            )

            page_operations.append(
                operation
            )


        messages_api.list.side_effect = (
            page_operations
        )


        def get_message(
            *,
            userId,
            id,
            format,
        ):

            self.assertEqual(
                userId,
                "me",
            )

            self.assertEqual(
                format,
                "full",
            )


            operation = Mock()

            operation.execute.return_value = (
                messages[id]
            )

            return operation


        messages_api.get.side_effect = (
            get_message
        )


        with (
            patch(
                (
                    "googleapis.services."
                    "gmail_sync."
                    "get_gmail_credentials"
                ),
                return_value=Mock(),
            ),
            patch(
                (
                    "googleapis.services."
                    "gmail_sync.build"
                ),
                return_value=service,
            ),
            patch(
                (
                    "googleapis.services."
                    "gmail_sync."
                    "MessageProcessor"
                )
            ) as processor,
            patch(
                (
                    "googleapis.services."
                    "gmail_sync."
                    "invalidate_conversation_cache"
                )
            ),
            patch(
                (
                    "googleapis.services."
                    "gmail_sync."
                    "get_channel_layer"
                ),
                return_value=Mock(),
            ),
            patch(
                (
                    "googleapis.services."
                    "gmail_sync."
                    "async_to_sync"
                )
            ) as async_to_sync,
        ):

            async_to_sync.return_value = (
                Mock()
            )


            result = (
                fetch_gmail_emails(
                    user=self.user,
                    email_account=(
                        self.account
                    ),
                )
            )


            return (
                result,
                messages_api,
                processor,
                async_to_sync,
            )


    def test_initial_history_paginates_and_uses_ninety_day_query(
        self,
    ):

        first = (
            self.gmail_message(
                message_id="gmail-1",
                thread_id="thread-1",
                body="First full body.",
                internal_date=(
                    "1788076800000"
                ),
            )
        )

        second = (
            self.gmail_message(
                message_id="gmail-2",
                thread_id="thread-2",
                body="Second full body.",
                internal_date=(
                    "1788163200000"
                ),
            )
        )


        (
            result,
            messages_api,
            _,
            async_to_sync,
        ) = (
            self.run_provider(
                pages=[
                    {
                        "messages": [
                            {
                                "id":
                                    "gmail-1"
                            },
                        ],

                        "nextPageToken":
                            "page-2",
                    },
                    {
                        "messages": [
                            {
                                "id":
                                    "gmail-2"
                            },
                        ],
                    },
                ],
                messages={
                    "gmail-1":
                        first,

                    "gmail-2":
                        second,
                },
            )
        )


        self.assertTrue(
            result[
                "initial_history"
            ]
        )

        self.assertEqual(
            result[
                "created"
            ],
            2,
        )


        self.assertEqual(
            messages_api
            .list.call_count,
            2,
        )


        first_call = (
            messages_api
            .list.call_args_list[0]
        )

        second_call = (
            messages_api
            .list.call_args_list[1]
        )


        self.assertEqual(
            first_call.kwargs[
                "maxResults"
            ],
            100,
        )


        self.assertIn(
            "after:",
            first_call.kwargs[
                "q"
            ],
        )

        self.assertIn(
            "{in:inbox in:sent}",
            first_call.kwargs[
                "q"
            ],
        )


        self.assertEqual(
            second_call.kwargs[
                "pageToken"
            ],
            "page-2",
        )


        self.account.refresh_from_db()

        self.assertIsNotNone(
            self.account
            .history_sync_completed_at
        )


        # Historical backfill must not produce one live browser
        # notification for every historical message.
        async_to_sync.assert_not_called()


    def test_full_body_and_recipient_history_are_persisted(
        self,
    ):

        from inbox.models import (
            InboxMessage,
        )


        message = (
            self.gmail_message(
                message_id=(
                    "gmail-full"
                ),
                thread_id=(
                    "thread-full"
                ),
                body=(
                    "This is the complete "
                    "message body that One UCH "
                    "must analyze."
                ),
                internal_date=(
                    "1788076800000"
                ),
            )
        )


        (
            _,
            _,
            processor,
            _,
        ) = (
            self.run_provider(
                pages=[
                    {
                        "messages": [
                            {
                                "id":
                                    "gmail-full"
                            },
                        ],
                    },
                ],
                messages={
                    "gmail-full":
                        message,
                },
            )
        )


        stored = (
            InboxMessage.objects.get(
                email_account=(
                    self.account
                ),
                external_message_id=(
                    "gmail-full"
                ),
            )
        )


        self.assertEqual(
            stored.body,
            (
                "This is the complete "
                "message body that One UCH "
                "must analyze."
            ),
        )


        self.assertNotEqual(
            stored.body,
            message[
                "snippet"
            ],
        )


        self.assertEqual(
            stored.sender,
            "customer@example.com",
        )


        self.assertEqual(
            stored.sender_meta,
            {
                "name":
                    "Customer Name",

                "email":
                    "customer@example.com",
            },
        )


        self.assertEqual(
            stored.recipient_meta[
                "to"
            ][0][
                "email"
            ],
            "pilot@gmail.com",
        )


        self.assertEqual(
            stored.recipient_meta[
                "cc"
            ][0][
                "email"
            ],
            "finance@example.com",
        )


        self.assertEqual(
            stored.recipient_meta[
                "bcc"
            ][0][
                "email"
            ],
            "audit@example.com",
        )


        self.assertEqual(
            stored.recipient_meta[
                "reply_to"
            ][0][
                "email"
            ],
            "support@example.com",
        )


        self.assertEqual(
            stored.recipients,
            (
                "pilot@gmail.com, "
                "finance@example.com, "
                "audit@example.com"
            ),
        )


        processor.return_value.process_message.assert_called_once()

        call = (
            processor.return_value
            .process_message
            .call_args
        )


        self.assertEqual(
            call.kwargs[
                "body"
            ],
            stored.body,
        )


    def test_provider_timestamp_and_sent_folder_are_preserved(
        self,
    ):

        from datetime import (
            timezone as datetime_timezone,
        )

        from inbox.models import (
            InboxMessage,
        )


        message = (
            self.gmail_message(
                message_id=(
                    "gmail-sent"
                ),
                thread_id=(
                    "thread-sent"
                ),
                body=(
                    "Sent body"
                ),
                internal_date=(
                    "1788076800000"
                ),
                labels=[
                    "SENT",
                ],
            )
        )


        self.run_provider(
            pages=[
                {
                    "messages": [
                        {
                            "id":
                                "gmail-sent"
                        },
                    ],
                },
            ],
            messages={
                "gmail-sent":
                    message,
            },
        )


        stored = (
            InboxMessage.objects.get(
                external_message_id=(
                    "gmail-sent"
                ),
                email_account=(
                    self.account
                ),
            )
        )


        expected = (
            timezone.datetime.fromtimestamp(
                1788076800,
                tz=(
                    datetime_timezone.utc
                ),
            )
        )


        self.assertEqual(
            stored.received_at,
            expected,
        )

        self.assertEqual(
            stored.direction,
            "outbound",
        )

        self.assertEqual(
            stored.folder,
            "sent",
        )


    def test_newest_message_remains_conversation_truth(
        self,
    ):

        from inbox.models import (
            Conversation,
        )


        newer = (
            self.gmail_message(
                message_id="gmail-new",
                thread_id="thread-same",
                body="New body",
                internal_date=(
                    "1788163200000"
                ),
            )
        )

        older = (
            self.gmail_message(
                message_id="gmail-old",
                thread_id="thread-same",
                body="Old body",
                internal_date=(
                    "1788076800000"
                ),
            )
        )


        self.run_provider(
            pages=[
                {
                    "messages": [
                        {
                            "id":
                                "gmail-new"
                        },
                        {
                            "id":
                                "gmail-old"
                        },
                    ],
                },
            ],
            messages={
                "gmail-new":
                    newer,

                "gmail-old":
                    older,
            },
        )


        conversation = (
            Conversation.objects.get(
                user=self.user,
                conversation_key=(
                    "gmail_thread-same"
                ),
            )
        )


        self.assertEqual(
            conversation
            .last_message
            .external_message_id,
            "gmail-new",
        )


    def test_partial_initial_failure_does_not_mark_history_complete(
        self,
    ):

        service = Mock()

        messages_api = (
            service
            .users.return_value
            .messages.return_value
        )


        page_operation = Mock()

        page_operation.execute.return_value = {
            "messages": [
                {
                    "id":
                        "broken-message"
                },
            ],
        }

        messages_api.list.return_value = (
            page_operation
        )


        broken = Mock()

        broken.execute.side_effect = (
            RuntimeError(
                "provider message unavailable"
            )
        )

        messages_api.get.return_value = (
            broken
        )


        with (
            patch(
                (
                    "googleapis.services."
                    "gmail_sync."
                    "get_gmail_credentials"
                ),
                return_value=Mock(),
            ),
            patch(
                (
                    "googleapis.services."
                    "gmail_sync.build"
                ),
                return_value=service,
            ),
        ):

            with self.assertRaisesRegex(
                RuntimeError,
                (
                    "Gmail partial sync failure: "
                    r"1 message\(s\) failed"
                ),
            ):

                fetch_gmail_emails(
                    user=self.user,
                    email_account=(
                        self.account
                    ),
                )


        self.account.refresh_from_db()


        self.assertIsNone(
            self.account
            .history_sync_completed_at
        )


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


    def test_initial_history_upgrades_existing_legacy_gmail_message(
        self,
    ):

        from datetime import (
            timezone as datetime_timezone,
        )

        from inbox.models import (
            Conversation,
            InboxMessage,
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
                    "gmail_legacy-thread"
                ),
                external_conversation_id=(
                    "legacy-thread"
                ),
                subject=(
                    "Legacy Gmail message"
                ),
            )
        )


        legacy = (
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
                folder="inbox",
                external_message_id=(
                    "legacy-gmail-id"
                ),
                external_conversation_id=(
                    "legacy-thread"
                ),
                sender=(
                    "old@example.com"
                ),
                recipients=(
                    self.account
                    .email_address
                ),
                sender_meta={},
                recipient_meta={},
                subject=(
                    "Legacy Gmail message"
                ),
                body=(
                    "Old preview only"
                ),
                received_at=(
                    timezone.now()
                ),
                is_read=False,
            )
        )


        original_pk = (
            legacy.pk
        )


        provider_message = (
            self.gmail_message(
                message_id=(
                    "legacy-gmail-id"
                ),
                thread_id=(
                    "legacy-thread"
                ),
                body=(
                    "Canonical full Gmail body."
                ),
                internal_date=(
                    "1788076800000"
                ),
            )
        )


        (
            result,
            _,
            _,
            _,
        ) = (
            self.run_provider(
                pages=[
                    {
                        "messages": [
                            {
                                "id":
                                    "legacy-gmail-id"
                            }
                        ]
                    }
                ],
                messages={
                    "legacy-gmail-id":
                        provider_message
                },
            )
        )


        self.assertEqual(
            result[
                "created"
            ],
            0,
        )

        self.assertEqual(
            result[
                "upgraded"
            ],
            1,
        )


        self.assertEqual(
            InboxMessage.objects
            .filter(
                email_account=(
                    self.account
                ),
                external_message_id=(
                    "legacy-gmail-id"
                ),
            )
            .count(),
            1,
        )


        legacy.refresh_from_db()


        self.assertEqual(
            legacy.pk,
            original_pk,
        )


        self.assertEqual(
            legacy.body,
            "Canonical full Gmail body.",
        )


        self.assertEqual(
            legacy.sender,
            "customer@example.com",
        )


        self.assertEqual(
            legacy.sender_meta[
                "email"
            ],
            "customer@example.com",
        )


        self.assertEqual(
            legacy.recipient_meta[
                "cc"
            ][0][
                "email"
            ],
            "finance@example.com",
        )


        self.assertEqual(
            legacy.recipient_meta[
                "bcc"
            ][0][
                "email"
            ],
            "audit@example.com",
        )


        self.assertEqual(
            legacy.recipient_meta[
                "reply_to"
            ][0][
                "email"
            ],
            "support@example.com",
        )


        expected_time = (
            timezone.datetime.fromtimestamp(
                1788076800,
                tz=(
                    datetime_timezone.utc
                ),
            )
        )


        self.assertEqual(
            legacy.received_at,
            expected_time,
        )


        self.account.refresh_from_db()


        self.assertIsNotNone(
            self.account
            .history_sync_completed_at
        )
