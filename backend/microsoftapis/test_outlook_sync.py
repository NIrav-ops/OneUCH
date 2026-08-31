from datetime import (
    timezone as datetime_timezone,
)

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

from django.utils import (
    timezone,
)

from email_accounts.models import (
    EmailAccount,
)

from inbox.models import (
    Conversation,
    InboxMessage,
    InboxSyncStatus,
    Organization,
    OrganizationUser,
)

from microsoftapis.services.outlook_sync import (
    fetch_outlook_emails,
)


User = get_user_model()


class OutlookInboundOutboundSyncTests(
    TestCase
):

    def setUp(self):
        self.user = (
            User.objects.create_user(
                email=(
                    "outlook-sync@oneuch.test"
                ),
                password="pass123",
            )
        )

        self.organization = (
            Organization.objects.create(
                name=(
                    "Outlook Sync Org"
                ),
                slug=(
                    "outlook-sync-org"
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
                account_type="outlook",
                email_address=(
                    "pilot@contoso.example"
                ),
                credential_status="active",
                is_active=True,
            )
        )

    def response(
        self,
        messages,
        *,
        status=200,
        text="",
    ):
        response = Mock()

        response.status_code = (
            status
        )

        response.text = (
            text
        )

        response.json.return_value = {
            "value": messages,
        }

        return response

    def inbound_message(
        self,
        *,
        external_id="in-1",
        conversation_id="conv-1",
        received=(
            "2026-08-30T08:00:00Z"
        ),
    ):
        return {
            "id":
                external_id,

            "conversationId":
                conversation_id,

            "subject":
                "Customer requirement",

            "bodyPreview":
                "Please confirm the rollout plan.",

            "receivedDateTime":
                received,

            "sentDateTime":
                "2026-08-30T07:59:00Z",

            "isRead":
                False,

            "from": {
                "emailAddress": {
                    "address":
                        "customer@example.com"
                }
            },

            "toRecipients": [
                {
                    "emailAddress": {
                        "address":
                            self.account.email_address
                    }
                }
            ],

            "hasAttachments":
                False,
        }

    def sent_message(
        self,
        *,
        external_id="out-1",
        conversation_id="conv-1",
        sent=(
            "2026-08-30T07:00:00Z"
        ),
        subject="Re: Customer requirement",
        body=(
            "We will share the rollout plan."
        ),
        recipient="customer@example.com",
    ):
        return {
            "id":
                external_id,

            "conversationId":
                conversation_id,

            "subject":
                subject,

            "bodyPreview":
                body,

            "receivedDateTime":
                sent,

            "sentDateTime":
                sent,

            "isRead":
                True,

            "from": {
                "emailAddress": {
                    "address":
                        self.account.email_address
                }
            },

            "toRecipients": [
                {
                    "emailAddress": {
                        "address":
                            recipient
                    }
                }
            ],

            "hasAttachments":
                False,
        }

    def run_sync(
        self,
        *,
        inbox,
        sent,
        sent_status=200,
    ):
        def graph_get(
            url,
            **kwargs,
        ):
            if (
                "/mailFolders/inbox/"
                in url
            ):
                return self.response(
                    inbox
                )

            if (
                "/mailFolders/sentitems/"
                in url
            ):
                return self.response(
                    sent,
                    status=sent_status,
                    text=(
                        "sent folder unavailable"
                        if sent_status != 200
                        else ""
                    ),
                )

            raise AssertionError(
                f"Unexpected Graph URL: {url}"
            )

        with (
            patch(
                "microsoftapis.services.outlook_sync."
                "get_microsoft_access_token",
                return_value="access-token",
            ),
            patch(
                "microsoftapis.services.outlook_sync."
                "requests.get",
                side_effect=graph_get,
            ) as graph_request,
            patch(
                "microsoftapis.services.outlook_sync."
                "MessageProcessor"
            ) as processor,
            patch(
                "microsoftapis.services.outlook_sync."
                "invalidate_conversation_cache"
            ),
            patch(
                "microsoftapis.services.outlook_sync."
                "get_channel_layer"
            ) as get_channel_layer,
            patch(
                "microsoftapis.services.outlook_sync."
                "async_to_sync"
            ) as async_to_sync,
        ):
            get_channel_layer.return_value = (
                Mock()
            )

            async_to_sync.return_value = (
                Mock()
            )

            fetch_outlook_emails(
                user=self.user,
                email_account=(
                    self.account
                ),
            )

            return (
                graph_request,
                processor,
            )

    def test_sync_persists_inbox_and_sent_directions(
        self,
    ):
        graph_request, processor = (
            self.run_sync(
                inbox=[
                    self.inbound_message()
                ],
                sent=[
                    self.sent_message()
                ],
            )
        )

        self.assertEqual(
            graph_request.call_count,
            2,
        )

        messages = (
            InboxMessage.objects
            .filter(
                email_account=(
                    self.account
                )
            )
            .order_by(
                "received_at"
            )
        )

        self.assertEqual(
            messages.count(),
            2,
        )

        outbound = messages[0]
        inbound = messages[1]

        self.assertEqual(
            outbound.direction,
            "outbound",
        )

        self.assertEqual(
            outbound.folder,
            "sent",
        )

        self.assertEqual(
            outbound.sender,
            self.account.email_address,
        )

        self.assertEqual(
            outbound.recipients,
            "customer@example.com",
        )

        self.assertEqual(
            inbound.direction,
            "inbound",
        )

        self.assertEqual(
            inbound.folder,
            "inbox",
        )

        self.assertEqual(
            inbound.sender,
            "customer@example.com",
        )

        self.assertEqual(
            inbound.recipients,
            self.account.email_address,
        )

        self.assertEqual(
            outbound.conversation_id,
            inbound.conversation_id,
        )

        conversation = (
            inbound.conversation
        )

        # Inbox is newer than the Sent Item in this
        # fixture. Folder-processing order must not
        # regress the conversation's last-message truth.
        self.assertEqual(
            conversation.last_message_id,
            inbound.id,
        )

        self.assertEqual(
            processor.return_value
            .process_message.call_count,
            2,
        )

        sync = (
            InboxSyncStatus.objects.get(
                user=self.user,
                platform="outlook",
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

    def test_sent_item_reconciles_existing_oneuch_outbound(
        self,
    ):
        local_conversation = (
            Conversation.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                email_account=(
                    self.account
                ),
                conversation_key=(
                    "local-proposal-customer"
                ),
                subject="Proposal",
            )
        )

        local_message = (
            InboxMessage.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                email_account=(
                    self.account
                ),
                conversation=(
                    local_conversation
                ),
                folder="inbox",
                platform="outlook",
                direction="outbound",
                external_message_id="sent",
                sender=(
                    self.account.email_address
                ),
                recipients=(
                    "customer@example.com"
                ),
                subject="Proposal",
                body=(
                    "Full body from One UCH."
                ),
                received_at=(
                    timezone.datetime(
                        2026,
                        8,
                        30,
                        7,
                        0,
                        tzinfo=(
                            datetime_timezone.utc
                        ),
                    )
                ),
                is_read=True,
                status="sent",
            )
        )

        self.run_sync(
            inbox=[],
            sent=[
                self.sent_message(
                    external_id=(
                        "graph-sent-2"
                    ),
                    conversation_id=(
                        "graph-conv-2"
                    ),
                    sent=(
                        "2026-08-30T07:01:00Z"
                    ),
                    subject="Proposal",
                    body=(
                        "Full body from One UCH."
                    ),
                )
            ],
        )

        self.assertEqual(
            InboxMessage.objects
            .filter(
                email_account=(
                    self.account
                )
            )
            .count(),
            1,
        )

        local_message.refresh_from_db()
        local_conversation.refresh_from_db()

        self.assertEqual(
            local_message.external_message_id,
            "graph-sent-2",
        )

        self.assertEqual(
            local_message.external_conversation_id,
            "graph-conv-2",
        )

        self.assertEqual(
            local_message.folder,
            "sent",
        )

        self.assertEqual(
            local_message.body,
            "Full body from One UCH.",
        )

        self.assertEqual(
            local_conversation.conversation_key,
            "outlook_graph-conv-2",
        )

        self.assertEqual(
            local_conversation.external_conversation_id,
            "graph-conv-2",
        )

    def test_provider_message_ids_remain_idempotent(
        self,
    ):
        inbox = [
            self.inbound_message()
        ]

        sent = [
            self.sent_message()
        ]

        self.run_sync(
            inbox=inbox,
            sent=sent,
        )

        self.run_sync(
            inbox=inbox,
            sent=sent,
        )

        self.assertEqual(
            InboxMessage.objects
            .filter(
                email_account=(
                    self.account
                )
            )
            .count(),
            2,
        )

        self.assertEqual(
            Conversation.objects
            .filter(
                user=self.user
            )
            .count(),
            1,
        )

    def test_sent_folder_failure_does_not_claim_complete_sync(
        self,
    ):
        with self.assertRaisesRegex(
            RuntimeError,
            "sentitems",
        ):
            self.run_sync(
                inbox=[
                    self.inbound_message()
                ],
                sent=[],
                sent_status=503,
            )

        self.assertEqual(
            InboxMessage.objects
            .filter(
                email_account=(
                    self.account
                )
            )
            .count(),
            0,
        )

        sync = (
            InboxSyncStatus.objects.get(
                user=self.user,
                platform="outlook",
            )
        )

        self.assertEqual(
            sync.status,
            "failed",
        )

        self.assertIn(
            "sentitems",
            sync.error_message,
        )


class OutlookHistoryCorrectnessTests(
    TestCase
):

    def setUp(
        self,
    ):

        self.user = (
            User.objects.create_user(
                email=(
                    "outlook-history@oneuch.test"
                ),
                password="pass123",
            )
        )


        self.organization = (
            Organization.objects.create(
                name=(
                    "Outlook History Org"
                ),
                slug=(
                    "outlook-history-org"
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
                account_type="outlook",
                email_address=(
                    "pilot@contoso.example"
                ),
                credential_status="active",
                is_active=True,
            )
        )


    def response(
        self,
        *,
        messages,
        status=200,
        next_link=None,
    ):

        response = Mock()

        response.status_code = (
            status
        )


        payload = {
            "value":
                messages,
        }


        if next_link:

            payload[
                "@odata.nextLink"
            ] = next_link


        response.json.return_value = (
            payload
        )

        response.text = ""

        return response


    def inbound(
        self,
        *,
        external_id,
        conversation_id,
        body,
        body_preview="Preview only",
        received=(
            "2026-08-30T08:00:00Z"
        ),
    ):

        return {
            "id":
                external_id,

            "conversationId":
                conversation_id,

            "subject":
                "Microsoft history test",

            "bodyPreview":
                body_preview,

            "body": {
                "contentType":
                    "text",

                "content":
                    body,
            },

            "receivedDateTime":
                received,

            "sentDateTime":
                "2026-08-30T07:59:00Z",

            "isRead":
                False,

            "from": {
                "emailAddress": {
                    "name":
                        "Customer Name",

                    "address":
                        "customer@example.com",
                },
            },

            "toRecipients": [
                {
                    "emailAddress": {
                        "name":
                            "Pilot User",

                        "address":
                            (
                                self.account
                                .email_address
                            ),
                    },
                },
            ],

            "ccRecipients": [
                {
                    "emailAddress": {
                        "name":
                            "Finance Team",

                        "address":
                            "finance@example.com",
                    },
                },
            ],

            "bccRecipients": [
                {
                    "emailAddress": {
                        "name":
                            "Audit Team",

                        "address":
                            "audit@example.com",
                    },
                },
            ],

            "replyTo": [
                {
                    "emailAddress": {
                        "name":
                            "Support",

                        "address":
                            "support@example.com",
                    },
                },
            ],

            "hasAttachments":
                True,

            "attachments": [
                {
                    "@odata.type":
                        (
                            "#microsoft.graph."
                            "fileAttachment"
                        ),

                    "id":
                        "attachment-1",

                    "name":
                        "proposal.pdf",

                    "contentType":
                        "application/pdf",
                },
            ],

            "flag": {
                "flagStatus":
                    "flagged",
            },
        }


    def sent(
        self,
        *,
        external_id,
        conversation_id,
        body,
        sent=(
            "2026-08-30T09:00:00Z"
        ),
    ):

        return {
            "id":
                external_id,

            "conversationId":
                conversation_id,

            "subject":
                "Sent history test",

            "bodyPreview":
                "Sent preview",

            "body": {
                "contentType":
                    "text",

                "content":
                    body,
            },

            "receivedDateTime":
                sent,

            "sentDateTime":
                sent,

            "isRead":
                True,

            "from": {
                "emailAddress": {
                    "name":
                        "Pilot User",

                    "address":
                        (
                            self.account
                            .email_address
                        ),
                },
            },

            "toRecipients": [
                {
                    "emailAddress": {
                        "name":
                            "Customer",

                        "address":
                            "customer@example.com",
                    },
                },
            ],

            "ccRecipients":
                [],

            "bccRecipients":
                [],

            "replyTo":
                [],

            "hasAttachments":
                False,

            "flag": {
                "flagStatus":
                    "notFlagged",
            },
        }


    def run_graph(
        self,
        graph_get,
    ):

        with (
            patch(
                (
                    "microsoftapis.services."
                    "outlook_sync."
                    "get_microsoft_access_token"
                ),
                return_value=(
                    "access-token"
                ),
            ),
            patch(
                (
                    "microsoftapis.services."
                    "outlook_sync."
                    "requests.get"
                ),
                side_effect=(
                    graph_get
                ),
            ) as request_mock,
            patch(
                (
                    "microsoftapis.services."
                    "outlook_sync."
                    "MessageProcessor"
                )
            ) as processor,
            patch(
                (
                    "microsoftapis.services."
                    "outlook_sync."
                    "invalidate_conversation_cache"
                )
            ),
            patch(
                (
                    "microsoftapis.services."
                    "outlook_sync."
                    "get_channel_layer"
                ),
                return_value=Mock(),
            ),
            patch(
                (
                    "microsoftapis.services."
                    "outlook_sync."
                    "async_to_sync"
                )
            ) as async_to_sync,
        ):

            async_to_sync.return_value = (
                Mock()
            )


            result = (
                fetch_outlook_emails(
                    user=self.user,
                    email_account=(
                        self.account
                    ),
                )
            )


            return (
                result,
                request_mock,
                processor,
                async_to_sync,
            )


    def test_initial_history_paginates_both_folders_and_marks_complete(
        self,
    ):

        inbox_next = (
            "https://graph.microsoft.com/"
            "v1.0/me/mailFolders/inbox/"
            "messages?$skiptoken=inbox-page-2"
        )


        inbound_one = (
            self.inbound(
                external_id=(
                    "history-in-1"
                ),
                conversation_id=(
                    "history-conv-1"
                ),
                body=(
                    "Complete inbound body one."
                ),
            )
        )


        inbound_two = (
            self.inbound(
                external_id=(
                    "history-in-2"
                ),
                conversation_id=(
                    "history-conv-2"
                ),
                body=(
                    "Complete inbound body two."
                ),
                received=(
                    "2026-08-30T08:30:00Z"
                ),
            )
        )


        sent_one = (
            self.sent(
                external_id=(
                    "history-out-1"
                ),
                conversation_id=(
                    "history-conv-3"
                ),
                body=(
                    "Complete outbound body."
                ),
            )
        )


        calls = {
            "inbox":
                0,

            "sentitems":
                0,
        }


        def graph_get(
            url,
            **kwargs,
        ):

            if url == inbox_next:

                calls[
                    "inbox"
                ] += 1

                self.assertNotIn(
                    "params",
                    kwargs,
                )

                return self.response(
                    messages=[
                        inbound_two
                    ]
                )


            if (
                "/mailFolders/inbox/"
                in url
            ):

                calls[
                    "inbox"
                ] += 1

                params = (
                    kwargs[
                        "params"
                    ]
                )


                self.assertEqual(
                    params[
                        "$top"
                    ],
                    100,
                )


                self.assertIn(
                    "receivedDateTime ge ",
                    params[
                        "$filter"
                    ],
                )


                self.assertIn(
                    "body,",
                    params[
                        "$select"
                    ],
                )


                self.assertIn(
                    "ccRecipients",
                    params[
                        "$select"
                    ],
                )


                self.assertIn(
                    "bccRecipients",
                    params[
                        "$select"
                    ],
                )


                self.assertIn(
                    "replyTo",
                    params[
                        "$select"
                    ],
                )


                self.assertEqual(
                    kwargs[
                        "headers"
                    ][
                        "Prefer"
                    ],
                    (
                        'outlook.'
                        'body-content-type="text"'
                    ),
                )


                return self.response(
                    messages=[
                        inbound_one
                    ],
                    next_link=(
                        inbox_next
                    ),
                )


            if (
                "/mailFolders/sentitems/"
                in url
            ):

                calls[
                    "sentitems"
                ] += 1


                self.assertIn(
                    "sentDateTime ge ",
                    kwargs[
                        "params"
                    ][
                        "$filter"
                    ],
                )


                return self.response(
                    messages=[
                        sent_one
                    ]
                )


            raise AssertionError(
                (
                    "Unexpected Graph URL: "
                    f"{url}"
                )
            )


        (
            result,
            request_mock,
            _,
            async_to_sync,
        ) = (
            self.run_graph(
                graph_get
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
            3,
        )


        self.assertEqual(
            request_mock.call_count,
            3,
        )


        self.assertEqual(
            calls,
            {
                "inbox":
                    2,

                "sentitems":
                    1,
            },
        )


        self.account.refresh_from_db()


        self.assertIsNotNone(
            self.account
            .history_sync_completed_at
        )


        # Historical backfill must not emit a live browser event.
        async_to_sync.assert_not_called()


    def test_full_body_recipient_metadata_attachment_and_flag_are_persisted(
        self,
    ):

        message = (
            self.inbound(
                external_id=(
                    "full-microsoft"
                ),
                conversation_id=(
                    "full-conversation"
                ),
                body=(
                    "This is the complete Microsoft "
                    "message body One UCH must analyze."
                ),
                body_preview=(
                    "Incomplete preview."
                ),
            )
        )


        def graph_get(
            url,
            **kwargs,
        ):

            if (
                "/mailFolders/inbox/"
                in url
            ):

                return self.response(
                    messages=[
                        message
                    ]
                )


            if (
                "/mailFolders/sentitems/"
                in url
            ):

                return self.response(
                    messages=[]
                )


            raise AssertionError(
                f"Unexpected Graph URL: {url}"
            )


        (
            _,
            _,
            processor,
            _,
        ) = (
            self.run_graph(
                graph_get
            )
        )


        stored = (
            InboxMessage.objects.get(
                email_account=(
                    self.account
                ),
                external_message_id=(
                    "full-microsoft"
                ),
            )
        )


        self.assertEqual(
            stored.body,
            (
                "This is the complete Microsoft "
                "message body One UCH must analyze."
            ),
        )


        self.assertNotEqual(
            stored.body,
            "Incomplete preview.",
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
            (
                self.account
                .email_address
            ),
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
                "pilot@contoso.example, "
                "finance@example.com, "
                "audit@example.com"
            ),
        )


        self.assertTrue(
            stored.is_starred
        )


        self.assertEqual(
            stored.attachment_meta,
            [
                {
                    "filename":
                        "proposal.pdf",

                    "attachment_id":
                        "attachment-1",

                    "mime_type":
                        "application/pdf",
                }
            ],
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


    def test_second_page_failure_keeps_initial_history_retryable(
        self,
    ):

        inbox_next = (
            "https://graph.microsoft.com/"
            "v1.0/me/mailFolders/inbox/"
            "messages?$skiptoken=broken"
        )


        first_message = (
            self.inbound(
                external_id=(
                    "uncommitted-page-message"
                ),
                conversation_id=(
                    "uncommitted-page-conv"
                ),
                body=(
                    "Should not persist because "
                    "provider completeness failed."
                ),
            )
        )


        def graph_get(
            url,
            **kwargs,
        ):

            if url == inbox_next:

                return self.response(
                    messages=[],
                    status=503,
                )


            if (
                "/mailFolders/inbox/"
                in url
            ):

                return self.response(
                    messages=[
                        first_message
                    ],
                    next_link=(
                        inbox_next
                    ),
                )


            raise AssertionError(
                f"Unexpected Graph URL: {url}"
            )


        with (
            patch(
                (
                    "microsoftapis.services."
                    "outlook_sync."
                    "get_microsoft_access_token"
                ),
                return_value=(
                    "access-token"
                ),
            ),
            patch(
                (
                    "microsoftapis.services."
                    "outlook_sync."
                    "requests.get"
                ),
                side_effect=(
                    graph_get
                ),
            ),
        ):

            with self.assertRaisesRegex(
                RuntimeError,
                "inbox",
            ):

                fetch_outlook_emails(
                    user=self.user,
                    email_account=(
                        self.account
                    ),
                )


        self.assertFalse(
            InboxMessage.objects
            .filter(
                email_account=(
                    self.account
                )
            )
            .exists()
        )


        self.account.refresh_from_db()


        self.assertIsNone(
            self.account
            .history_sync_completed_at
        )


        sync = (
            InboxSyncStatus.objects.get(
                user=self.user,
                platform="outlook",
            )
        )


        self.assertEqual(
            sync.status,
            "failed",
        )


    def test_html_body_is_normalized_to_text(
        self,
    ):

        message = (
            self.inbound(
                external_id=(
                    "html-microsoft"
                ),
                conversation_id=(
                    "html-conversation"
                ),
                body=(
                    "<div>Hello <b>Customer</b></div>"
                    "<p>Please approve.</p>"
                ),
            )
        )


        message[
            "body"
        ][
            "contentType"
        ] = "html"


        def graph_get(
            url,
            **kwargs,
        ):

            if (
                "/mailFolders/inbox/"
                in url
            ):

                return self.response(
                    messages=[
                        message
                    ]
                )


            if (
                "/mailFolders/sentitems/"
                in url
            ):

                return self.response(
                    messages=[]
                )


            raise AssertionError(
                f"Unexpected Graph URL: {url}"
            )


        self.run_graph(
            graph_get
        )


        stored = (
            InboxMessage.objects.get(
                external_message_id=(
                    "html-microsoft"
                )
            )
        )


        self.assertIn(
            "Hello",
            stored.body,
        )


        self.assertIn(
            "Customer",
            stored.body,
        )


        self.assertIn(
            "Please approve.",
            stored.body,
        )


        self.assertNotIn(
            "<div>",
            stored.body,
        )


    def test_initial_history_upgrades_existing_legacy_outlook_message(
        self,
    ):

        from inbox.models import (
            Conversation,
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
                    "outlook_legacy-conversation"
                ),
                external_conversation_id=(
                    "legacy-conversation"
                ),
                subject=(
                    "Legacy Outlook message"
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
                platform="outlook",
                direction="inbound",
                folder="inbox",
                external_message_id=(
                    "legacy-outlook-id"
                ),
                external_conversation_id=(
                    "legacy-conversation"
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
                    "Legacy Outlook message"
                ),
                body=(
                    "Legacy body preview"
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
            self.inbound(
                external_id=(
                    "legacy-outlook-id"
                ),
                conversation_id=(
                    "legacy-conversation"
                ),
                body=(
                    "Canonical full Outlook body."
                ),
                body_preview=(
                    "Short preview"
                ),
            )
        )


        def graph_get(
            url,
            **kwargs,
        ):

            if (
                "/mailFolders/inbox/"
                in url
            ):

                return self.response(
                    messages=[
                        provider_message
                    ]
                )


            if (
                "/mailFolders/sentitems/"
                in url
            ):

                return self.response(
                    messages=[]
                )


            raise AssertionError(
                f"Unexpected Graph URL: {url}"
            )


        (
            result,
            _,
            _,
            _,
        ) = (
            self.run_graph(
                graph_get
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
                    "legacy-outlook-id"
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
            "Canonical full Outlook body.",
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


        self.account.refresh_from_db()


        self.assertIsNotNone(
            self.account
            .history_sync_completed_at
        )
