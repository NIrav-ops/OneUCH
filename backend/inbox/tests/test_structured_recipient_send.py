import base64

from email import (
    message_from_bytes,
)

from email.utils import (
    getaddresses,
)

from unittest.mock import (
    MagicMock,
    patch,
)

from django.contrib.auth import (
    get_user_model,
)

from django.utils import (
    timezone,
)

from rest_framework.response import (
    Response,
)

from rest_framework.test import (
    APITestCase,
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

from inbox.services.recipient_payload import (
    normalize_recipient_buckets,
)

from microsoftapis.services.outlook_sync import (
    _find_local_outbound_candidate,
)


User = get_user_model()


class StructuredRecipientSendTests(
    APITestCase
):

    def setUp(
        self,
    ):

        self.user = (
            User.objects.create_user(
                email=(
                    "p2c-user@oneuch.local"
                ),
                password="test-password-123",
            )
        )


        self.organization = (
            Organization.objects.create(
                name="P2C Organization",
                slug="p2c-organization",
            )
        )


        OrganizationUser.objects.create(
            user=self.user,
            organization=(
                self.organization
            ),
            role="member",
        )


        self.gmail = (
            EmailAccount.objects.create(
                user=self.user,
                email_address=(
                    "p2c@gmail.com"
                ),
                account_type="gmail",
                credential_status="active",
                is_active=True,
            )
        )


        self.outlook = (
            EmailAccount.objects.create(
                user=self.user,
                email_address=(
                    "p2c@outlook.com"
                ),
                account_type="outlook",
                credential_status="active",
                is_active=True,
            )
        )


        self.client.force_authenticate(
            user=self.user
        )


    def payload(
        self,
        account,
    ):
        return {
            "to": [
                {
                    "name":
                        "Alice Customer",

                    "email":
                        "alice@example.com",
                }
            ],

            "cc": [
                {
                    "name":
                        "Bob Finance",

                    "email":
                        "bob@example.com",
                }
            ],

            "bcc": [
                {
                    "name":
                        "Carol Audit",

                    "email":
                        "carol@example.com",
                }
            ],

            "subject":
                "P2C recipient test",

            "body":
                "Structured recipient body",

            "account_id":
                account.id,
        }


    def test_recipient_normalizer_deduplicates_across_roles(
        self,
    ):

        meta, flat = (
            normalize_recipient_buckets(
                to=[
                    {
                        "email":
                            "same@example.com"
                    }
                ],
                cc=[
                    {
                        "email":
                            "same@example.com"
                    },
                    {
                        "email":
                            "cc@example.com"
                    },
                ],
                bcc=[
                    {
                        "email":
                            "cc@example.com"
                    },
                    {
                        "email":
                            "bcc@example.com"
                    },
                ],
            )
        )


        self.assertEqual(
            [
                item[
                    "email"
                ]
                for item
                in meta[
                    "to"
                ]
            ],
            [
                "same@example.com"
            ],
        )


        self.assertEqual(
            [
                item[
                    "email"
                ]
                for item
                in meta[
                    "cc"
                ]
            ],
            [
                "cc@example.com"
            ],
        )


        self.assertEqual(
            [
                item[
                    "email"
                ]
                for item
                in meta[
                    "bcc"
                ]
            ],
            [
                "bcc@example.com"
            ],
        )


        self.assertEqual(
            flat,
            (
                "same@example.com, "
                "cc@example.com, "
                "bcc@example.com"
            ),
        )


    def test_gmail_send_uses_to_cc_bcc_headers_and_persists_meta(
        self,
    ):

        service = (
            MagicMock()
        )


        (
            service
            .users
            .return_value
            .messages
            .return_value
            .send
            .return_value
            .execute
            .return_value
        ) = {
            "id":
                "gmail-provider-p2c"
        }


        with (
            patch(
                "inbox.views.send_message."
                "get_gmail_credentials",
                return_value=object(),
            ),
            patch(
                "inbox.views.send_message.build",
                return_value=service,
            ),
            patch(
                "inbox.views.send_message."
                "get_channel_layer",
            ),
            patch(
                "inbox.views.send_message."
                "async_to_sync",
                return_value=(
                    lambda *args, **kwargs:
                        None
                ),
            ),
        ):

            response = (
                self.client.post(
                    "/api/inbox/send/",
                    self.payload(
                        self.gmail
                    ),
                    format="json",
                )
            )


        self.assertEqual(
            response.status_code,
            200,
        )


        send_call = (
            service
            .users
            .return_value
            .messages
            .return_value
            .send
            .call_args
        )


        raw = (
            send_call.kwargs[
                "body"
            ][
                "raw"
            ]
        )


        mime = (
            message_from_bytes(
                base64
                .urlsafe_b64decode(
                    raw.encode()
                )
            )
        )


        to_addresses = {
            address
            for _, address
            in getaddresses(
                [
                    mime[
                        "To"
                    ]
                ]
            )
        }


        cc_addresses = {
            address
            for _, address
            in getaddresses(
                [
                    mime[
                        "Cc"
                    ]
                ]
            )
        }


        bcc_addresses = {
            address
            for _, address
            in getaddresses(
                [
                    mime[
                        "Bcc"
                    ]
                ]
            )
        }


        self.assertEqual(
            to_addresses,
            {
                "alice@example.com"
            },
        )

        self.assertEqual(
            cc_addresses,
            {
                "bob@example.com"
            },
        )

        self.assertEqual(
            bcc_addresses,
            {
                "carol@example.com"
            },
        )


        sent = (
            InboxMessage.objects.get(
                id=response.data[
                    "message_id"
                ]
            )
        )


        self.assertEqual(
            sent.folder,
            "sent",
        )

        self.assertEqual(
            sent.sender_meta[
                "email"
            ],
            "p2c@gmail.com",
        )

        self.assertEqual(
            sent.recipient_meta[
                "cc"
            ][0][
                "email"
            ],
            "bob@example.com",
        )

        self.assertEqual(
            sent.recipient_meta[
                "bcc"
            ][0][
                "email"
            ],
            "carol@example.com",
        )


    def test_outlook_send_uses_graph_to_cc_bcc_and_persists_meta(
        self,
    ):

        graph_response = (
            MagicMock()
        )

        graph_response.status_code = (
            202
        )


        with (
            patch(
                "inbox.views.send_message."
                "get_microsoft_access_token",
                return_value="token",
            ),
            patch(
                "inbox.views.send_message."
                "requests.post",
                return_value=(
                    graph_response
                ),
            ) as mocked_post,
            patch(
                "inbox.views.send_message."
                "get_channel_layer",
            ),
            patch(
                "inbox.views.send_message."
                "async_to_sync",
                return_value=(
                    lambda *args, **kwargs:
                        None
                ),
            ),
        ):

            response = (
                self.client.post(
                    "/api/inbox/send/",
                    self.payload(
                        self.outlook
                    ),
                    format="json",
                )
            )


        self.assertEqual(
            response.status_code,
            200,
        )


        message = (
            mocked_post
            .call_args
            .kwargs[
                "json"
            ][
                "message"
            ]
        )


        self.assertEqual(
            message[
                "toRecipients"
            ][0][
                "emailAddress"
            ][
                "address"
            ],
            "alice@example.com",
        )

        self.assertEqual(
            message[
                "ccRecipients"
            ][0][
                "emailAddress"
            ][
                "address"
            ],
            "bob@example.com",
        )

        self.assertEqual(
            message[
                "bccRecipients"
            ][0][
                "emailAddress"
            ][
                "address"
            ],
            "carol@example.com",
        )


        sent = (
            InboxMessage.objects.get(
                id=response.data[
                    "message_id"
                ]
            )
        )


        self.assertEqual(
            sent.folder,
            "sent",
        )

        self.assertEqual(
            sent.recipient_meta[
                "to"
            ][0][
                "name"
            ],
            "Alice Customer",
        )

        self.assertEqual(
            sent.recipient_meta[
                "cc"
            ][0][
                "name"
            ],
            "Bob Finance",
        )

        self.assertEqual(
            sent.recipient_meta[
                "bcc"
            ][0][
                "name"
            ],
            "Carol Audit",
        )


    def test_draft_preserves_roles_and_send_draft_forwards_them(
        self,
    ):

        response = (
            self.client.post(
                "/api/inbox/draft/save/",
                {
                    "to": [
                        {
                            "name":
                                "Draft To",

                            "email":
                                "draft-to@example.com",
                        }
                    ],

                    "cc": [
                        {
                            "name":
                                "Draft Cc",

                            "email":
                                "draft-cc@example.com",
                        }
                    ],

                    "bcc": [
                        {
                            "name":
                                "Draft Bcc",

                            "email":
                                "draft-bcc@example.com",
                        }
                    ],

                    "subject":
                        "Structured draft",

                    "body":
                        "Draft body",

                    "account_id":
                        self.gmail.id,
                },
                format="json",
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        draft = (
            InboxMessage.objects.get(
                id=response.data[
                    "draft_id"
                ]
            )
        )


        self.assertEqual(
            draft.recipient_meta[
                "to"
            ][0][
                "email"
            ],
            "draft-to@example.com",
        )

        self.assertEqual(
            draft.recipient_meta[
                "cc"
            ][0][
                "email"
            ],
            "draft-cc@example.com",
        )

        self.assertEqual(
            draft.recipient_meta[
                "bcc"
            ][0][
                "email"
            ],
            "draft-bcc@example.com",
        )


        list_response = (
            self.client.get(
                "/api/inbox/draft/list/"
            )
        )


        self.assertEqual(
            list_response.status_code,
            200,
        )

        self.assertEqual(
            list_response.data[
                0
            ][
                "recipient_meta"
            ][
                "bcc"
            ][0][
                "email"
            ],
            "draft-bcc@example.com",
        )


        with patch(
            "inbox.views.send_message."
            "UnifiedSendMessageAPIView."
            "send_with_data"
        ) as mocked_send:

            mocked_send.return_value = (
                Response(
                    {
                        "status":
                            "sent",

                        "conversation_id":
                            draft
                            .conversation_id,

                        "message_id":
                            999,
                    },
                    status=200,
                )
            )


            send_response = (
                self.client.post(
                    (
                        "/api/inbox/draft/send/"
                        + str(
                            draft.id
                        )
                        + "/"
                    ),
                    {},
                    format="json",
                )
            )


        self.assertEqual(
            send_response.status_code,
            200,
        )


        payload = (
            mocked_send
            .call_args
            .kwargs[
                "data"
            ]
        )


        self.assertEqual(
            payload[
                "to"
            ][0][
                "email"
            ],
            "draft-to@example.com",
        )

        self.assertEqual(
            payload[
                "cc"
            ][0][
                "email"
            ],
            "draft-cc@example.com",
        )

        self.assertEqual(
            payload[
                "bcc"
            ][0][
                "email"
            ],
            "draft-bcc@example.com",
        )


    def test_outlook_reconciliation_matches_structured_to_only(
        self,
    ):

        conversation = (
            Conversation.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                email_account=(
                    self.outlook
                ),
                subject="Reconcile",
                conversation_key=(
                    "p2c-reconcile"
                ),
            )
        )


        local = (
            InboxMessage.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                email_account=(
                    self.outlook
                ),
                folder="sent",
                platform="outlook",
                direction="outbound",
                conversation=(
                    conversation
                ),
                external_message_id="sent",
                sender=(
                    self.outlook
                    .email_address
                ),
                recipients=(
                    "to@example.com, "
                    "cc@example.com, "
                    "bcc@example.com"
                ),
                sender_meta={
                    "name":
                        "",

                    "email":
                        self.outlook
                        .email_address,
                },
                recipient_meta={
                    "to": [
                        {
                            "name":
                                "",

                            "email":
                                "to@example.com",
                        }
                    ],

                    "cc": [
                        {
                            "name":
                                "",

                            "email":
                                "cc@example.com",
                        }
                    ],

                    "bcc": [
                        {
                            "name":
                                "",

                            "email":
                                "bcc@example.com",
                        }
                    ],

                    "reply_to": [],
                },
                subject="Reconcile",
                body="Body",
                received_at=(
                    timezone.now()
                ),
                is_read=True,
                is_draft=False,
                status="sent",
            )
        )


        candidate = (
            _find_local_outbound_candidate(
                user=self.user,
                email_account=(
                    self.outlook
                ),
                subject="Reconcile",
                recipients=[
                    "to@example.com"
                ],
                body_preview="Body",
                sent_at=(
                    local.received_at
                ),
            )
        )


        self.assertIsNotNone(
            candidate
        )

        self.assertEqual(
            candidate.id,
            local.id,
        )
