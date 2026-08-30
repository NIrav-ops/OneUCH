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
