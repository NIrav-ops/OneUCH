from unittest.mock import (
    patch,
)

from django.contrib.auth import (
    get_user_model,
)

from django.utils import (
    timezone,
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


class ReplyRecipientOverrideContractTests(
    APITestCase
):

    def setUp(
        self,
    ):
        User = (
            get_user_model()
        )


        self.user = (
            User.objects.create_user(
                email=(
                    "recipient-contract@oneuch.local"
                ),
                password=(
                    "test-password-123"
                ),
            )
        )


        self.organization = (
            Organization.objects.create(
                name=(
                    "Reply Recipient Contract"
                ),
                slug=(
                    "reply-recipient-contract"
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
                email_address=(
                    "recipient-contract@oneuch.local"
                ),
                account_type="gmail",
                credential_status="active",
                is_active=True,
            )
        )


        self.conversation = (
            Conversation.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                email_account=(
                    self.account
                ),
                subject=(
                    "Editable reply recipients"
                ),
                conversation_key=(
                    "editable-reply-recipients"
                ),
                external_conversation_id=(
                    "gmail-thread-contract"
                ),
            )
        )


        self.message = (
            InboxMessage.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                email_account=(
                    self.account
                ),
                folder="inbox",
                platform="gmail",
                direction="inbound",
                conversation=(
                    self.conversation
                ),
                external_message_id=(
                    "gmail-message-contract"
                ),
                external_conversation_id=(
                    "gmail-thread-contract"
                ),
                sender=(
                    "customer@example.com"
                ),
                sender_meta={
                    "name":
                        "Customer",

                    "email":
                        "customer@example.com",
                },
                recipients=(
                    "recipient-contract@oneuch.local"
                ),
                recipient_meta={
                    "to": [
                        {
                            "name":
                                "",

                            "email":
                                "recipient-contract@oneuch.local",
                        },
                        {
                            "name":
                                "Project Lead",

                            "email":
                                "lead@example.com",
                        },
                    ],

                    "cc": [
                        {
                            "name":
                                "Finance",

                            "email":
                                "finance@example.com",
                        }
                    ],

                    "bcc": [
                        {
                            "name":
                                "Hidden",

                            "email":
                                "hidden@example.com",
                        }
                    ],

                    "reply_to": [
                        {
                            "name":
                                "Support",

                            "email":
                                "support@example.com",
                        }
                    ],
                },
                subject=(
                    "Editable reply recipients"
                ),
                body=(
                    "Please review."
                ),
                received_at=(
                    timezone.now()
                ),
                is_read=True,
                status="sent",
            )
        )


        self.url = (
            "/api/inbox/conversations/"
            + str(
                self.conversation.id
            )
            + "/reply/"
        )


        self.client.force_authenticate(
            user=self.user
        )


    def test_reply_preflight_is_read_only(
        self,
    ):
        before = (
            InboxMessage.objects.count()
        )


        response = (
            self.client.get(
                self.url
                + "?mode=reply"
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        self.assertEqual(
            response.data["mode"],
            "reply",
        )


        self.assertEqual(
            [
                item["email"]
                for item
                in response.data[
                    "recipient_meta"
                ]["to"]
            ],
            [
                "support@example.com"
            ],
        )


        self.assertEqual(
            response.data[
                "recipient_meta"
            ]["cc"],
            [],
        )

        self.assertEqual(
            response.data[
                "recipient_meta"
            ]["bcc"],
            [],
        )


        self.assertEqual(
            InboxMessage.objects.count(),
            before,
        )


    def test_reply_all_preflight_excludes_self_and_source_bcc(
        self,
    ):
        response = (
            self.client.get(
                self.url
                + "?mode=reply_all"
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        meta = (
            response.data[
                "recipient_meta"
            ]
        )


        self.assertEqual(
            [
                item["email"]
                for item
                in meta["to"]
            ],
            [
                "support@example.com"
            ],
        )


        self.assertEqual(
            [
                item["email"]
                for item
                in meta["cc"]
            ],
            [
                "lead@example.com",
                "finance@example.com",
            ],
        )


        self.assertEqual(
            meta["bcc"],
            [],
        )


        flat = (
            response.data[
                "recipients"
            ]
        )


        self.assertNotIn(
            "recipient-contract@oneuch.local",
            flat,
        )

        self.assertNotIn(
            "hidden@example.com",
            flat,
        )


    @patch(
        "inbox.views.reply."
        "send_email_task.delay"
    )
    def test_post_accepts_explicit_to_cc_bcc(
        self,
        mocked_send,
    ):
        response = (
            self.client.post(
                self.url,
                {
                    "body":
                        "Updated recipient set.",

                    "mode":
                        "reply",

                    "to": [
                        {
                            "name":
                                "Customer",

                            "email":
                                "new.customer@example.com",
                        },
                    ],

                    "cc": [
                        {
                            "name":
                                "Finance",

                            "email":
                                "finance@example.com",
                        },
                    ],

                    "bcc": [
                        {
                            "name":
                                "Audit",

                            "email":
                                "audit@example.com",
                        },
                    ],
                },
                format="json",
            )
        )


        self.assertEqual(
            response.status_code,
            202,
        )


        reply = (
            InboxMessage.objects
            .filter(
                direction="outbound"
            )
            .latest("id")
        )


        self.assertEqual(
            [
                item["email"]
                for item
                in reply
                .recipient_meta["to"]
            ],
            [
                "new.customer@example.com"
            ],
        )


        self.assertEqual(
            [
                item["email"]
                for item
                in reply
                .recipient_meta["cc"]
            ],
            [
                "finance@example.com"
            ],
        )


        self.assertEqual(
            [
                item["email"]
                for item
                in reply
                .recipient_meta["bcc"]
            ],
            [
                "audit@example.com"
            ],
        )


        mocked_send.assert_called_once_with(
            self.account.id,
            "new.customer@example.com",
            "Re: Editable reply recipients",
            "Updated recipient set.",
            reply.id,
        )


    @patch(
        "inbox.views.reply."
        "send_email_task.delay"
    )
    def test_override_deduplicates_across_recipient_roles(
        self,
        mocked_send,
    ):
        response = (
            self.client.post(
                self.url,
                {
                    "body":
                        "Deduplicate recipients.",

                    "mode":
                        "reply_all",

                    "to": [
                        {
                            "email":
                                "customer@example.com"
                        }
                    ],

                    "cc": [
                        {
                            "email":
                                "customer@example.com"
                        },
                        {
                            "email":
                                "finance@example.com"
                        },
                    ],

                    "bcc": [
                        {
                            "email":
                                "finance@example.com"
                        },
                        {
                            "email":
                                "audit@example.com"
                        },
                    ],
                },
                format="json",
            )
        )


        self.assertEqual(
            response.status_code,
            202,
        )


        reply = (
            InboxMessage.objects
            .filter(
                direction="outbound"
            )
            .latest("id")
        )


        self.assertEqual(
            [
                item["email"]
                for item
                in reply
                .recipient_meta["to"]
            ],
            [
                "customer@example.com"
            ],
        )


        self.assertEqual(
            [
                item["email"]
                for item
                in reply
                .recipient_meta["cc"]
            ],
            [
                "finance@example.com"
            ],
        )


        self.assertEqual(
            [
                item["email"]
                for item
                in reply
                .recipient_meta["bcc"]
            ],
            [
                "audit@example.com"
            ],
        )


        mocked_send.assert_called_once_with(
            self.account.id,
            "customer@example.com",
            "Re: Editable reply recipients",
            "Deduplicate recipients.",
            reply.id,
            "reply_all",
        )


    @patch(
        "inbox.views.reply."
        "send_email_task.delay"
    )
    def test_explicit_override_requires_to_recipient(
        self,
        mocked_send,
    ):
        response = (
            self.client.post(
                self.url,
                {
                    "body":
                        "Invalid override.",

                    "mode":
                        "reply",

                    "to":
                        [],

                    "cc": [
                        {
                            "email":
                                "finance@example.com"
                        }
                    ],

                    "bcc":
                        [],
                },
                format="json",
            )
        )


        self.assertEqual(
            response.status_code,
            400,
        )


        self.assertEqual(
            response.data["error"],
            (
                "At least one valid To "
                "recipient is required."
            ),
        )


        self.assertFalse(
            InboxMessage.objects
            .filter(
                direction="outbound"
            )
            .exists()
        )


        mocked_send.assert_not_called()


    @patch(
        "inbox.views.reply."
        "bind_outbound_message"
    )
    @patch(
        "inbox.views.reply."
        "claim_outbound_intent"
    )
    @patch(
        "inbox.views.reply."
        "build_outbound_fingerprint"
    )
    @patch(
        "inbox.views.reply."
        "resolve_outbound_idempotency_key"
    )
    @patch(
        "inbox.views.reply."
        "send_email_task.delay"
    )
    def test_explicit_recipients_participate_in_idempotency_fingerprint(
        self,
        mocked_send,
        mocked_key,
        mocked_fingerprint,
        mocked_claim,
        mocked_bind,
    ):
        mocked_key.return_value = (
            "recipient-idempotency-key"
        )

        mocked_fingerprint.return_value = (
            "recipient-fingerprint"
        )

        mocked_claim.return_value = (
            {
                "state":
                    "claimed"
            },
            True,
        )


        response = (
            self.client.post(
                self.url,
                {
                    "body":
                        "Recipient-aware retry.",

                    "mode":
                        "reply",

                    "to": [
                        {
                            "email":
                                "customer@example.com"
                        }
                    ],

                    "cc": [
                        {
                            "email":
                                "finance@example.com"
                        }
                    ],

                    "bcc":
                        [],
                },
                format="json",
            )
        )


        self.assertEqual(
            response.status_code,
            202,
        )


        fingerprint_payload = (
            mocked_fingerprint
            .call_args
            .kwargs[
                "payload"
            ]
        )


        self.assertIn(
            "recipient_meta",
            fingerprint_payload,
        )


        self.assertEqual(
            [
                item["email"]
                for item
                in fingerprint_payload[
                    "recipient_meta"
                ]["to"]
            ],
            [
                "customer@example.com"
            ],
        )


        self.assertEqual(
            [
                item["email"]
                for item
                in fingerprint_payload[
                    "recipient_meta"
                ]["cc"]
            ],
            [
                "finance@example.com"
            ],
        )


        mocked_send.assert_called_once()

        mocked_bind.assert_called_once()
