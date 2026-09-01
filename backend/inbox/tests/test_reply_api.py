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


class ReplyConversationAPITests(
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
                    "reply-user@oneuch.local"
                ),
                password=(
                    "test-password-123"
                ),
            )
        )


        self.organization = (
            Organization.objects.create(
                name=(
                    "Reply Test Organization"
                ),
                slug=(
                    "reply-test-organization"
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


        self.email_account = (
            EmailAccount.objects.create(
                user=self.user,
                email_address=(
                    "reply-user@oneuch.local"
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
                    self.email_account
                ),
                subject=(
                    "Customer requirement"
                ),
                conversation_key=(
                    "reply-test-conversation"
                ),
                external_conversation_id=(
                    "gmail-thread-001"
                ),
            )
        )


        self.inbound_message = (
            InboxMessage.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                email_account=(
                    self.email_account
                ),
                folder="inbox",
                platform="gmail",
                direction="inbound",
                conversation=(
                    self.conversation
                ),
                external_message_id=(
                    "external-message-001"
                ),
                external_conversation_id=(
                    "gmail-thread-001"
                ),
                sender=(
                    "customer@example.com"
                ),
                recipients=(
                    "reply-user@oneuch.local"
                ),
                subject=(
                    "Customer requirement"
                ),
                body=(
                    "Please share an update."
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


    def test_reply_requires_authentication(
        self,
    ):
        response = (
            self.client.post(
                self.url,
                {
                    "body":
                        "Test reply"
                },
                format="json",
            )
        )


        self.assertIn(
            response.status_code,
            {
                401,
                403,
            },
        )


    def test_reply_rejects_empty_body(
        self,
    ):
        self.client.force_authenticate(
            user=self.user
        )


        response = (
            self.client.post(
                self.url,
                {
                    "body":
                        ""
                },
                format="json",
            )
        )


        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertEqual(
            response.data[
                "error"
            ],
            "Reply body is required",
        )


    def test_reply_rejects_unknown_mode(
        self,
    ):
        self.client.force_authenticate(
            user=self.user
        )


        response = (
            self.client.post(
                self.url,
                {
                    "body":
                        "Body",

                    "mode":
                        "everyone",
                },
                format="json",
            )
        )


        self.assertEqual(
            response.status_code,
            400,
        )


    def test_user_cannot_reply_to_another_users_conversation(
        self,
    ):
        User = (
            get_user_model()
        )


        other_user = (
            User.objects.create_user(
                email=(
                    "other-user@oneuch.local"
                ),
                password=(
                    "test-password-123"
                ),
            )
        )


        other_organization = (
            Organization.objects.create(
                name="Other Organization",
                slug="other-organization",
            )
        )


        OrganizationUser.objects.create(
            user=other_user,
            organization=(
                other_organization
            ),
            role="member",
        )


        other_conversation = (
            Conversation.objects.create(
                user=other_user,
                organization=(
                    other_organization
                ),
                subject=(
                    "Private conversation"
                ),
                conversation_key=(
                    "other-users-conversation"
                ),
            )
        )


        self.client.force_authenticate(
            user=self.user
        )


        response = (
            self.client.post(
                (
                    "/api/inbox/conversations/"
                    + str(
                        other_conversation.id
                    )
                    + "/reply/"
                ),
                {
                    "body":
                        "Unauthorized reply"
                },
                format="json",
            )
        )


        self.assertEqual(
            response.status_code,
            404,
        )


    @patch(
        "inbox.views.reply."
        "send_email_task.delay"
    )
    def test_legacy_reply_preserves_backward_compatibility(
        self,
        mocked_send_delay,
    ):
        self.client.force_authenticate(
            user=self.user
        )


        response = (
            self.client.post(
                self.url,
                {
                    "body":
                        "Here is the requested update."
                },
                format="json",
            )
        )


        self.assertEqual(
            response.status_code,
            202,
        )


        reply = (
            InboxMessage.objects.get(
                conversation=(
                    self.conversation
                ),
                direction="outbound",
            )
        )


        self.assertEqual(
            reply.recipients,
            "customer@example.com",
        )

        self.assertEqual(
            reply.recipient_meta[
                "to"
            ][0][
                "email"
            ],
            "customer@example.com",
        )

        self.assertEqual(
            reply.folder,
            "outbox",
        )

        self.assertEqual(
            reply.in_reply_to,
            "external-message-001",
        )

        self.assertEqual(
            reply.external_conversation_id,
            "gmail-thread-001",
        )


        mocked_send_delay.assert_called_once_with(
            self.email_account.id,
            "customer@example.com",
            "Re: Customer requirement",
            (
                "Here is the "
                "requested update."
            ),
            reply.id,
        )


    @patch(
        "inbox.views.reply."
        "send_email_task.delay"
    )
    def test_reply_prefers_structured_reply_to(
        self,
        mocked_send_delay,
    ):
        self.inbound_message.sender_meta = {
            "name":
                "Customer",

            "email":
                "customer@example.com",
        }

        self.inbound_message.recipient_meta = {
            "to": [
                {
                    "name":
                        "",

                    "email":
                        "reply-user@oneuch.local",
                }
            ],

            "cc":
                [],

            "bcc":
                [],

            "reply_to": [
                {
                    "name":
                        "Support Desk",

                    "email":
                        "support@example.com",
                }
            ],
        }

        self.inbound_message.save(
            update_fields=[
                "sender_meta",
                "recipient_meta",
            ]
        )


        self.client.force_authenticate(
            user=self.user
        )


        response = (
            self.client.post(
                self.url,
                {
                    "body":
                        "Reply-To test"
                },
                format="json",
            )
        )


        self.assertEqual(
            response.status_code,
            202,
        )


        reply = (
            InboxMessage.objects.get(
                direction="outbound"
            )
        )


        self.assertEqual(
            reply.recipients,
            "support@example.com",
        )

        self.assertEqual(
            reply.recipient_meta[
                "to"
            ][0][
                "name"
            ],
            "Support Desk",
        )


        mocked_send_delay.assert_called_once()


    @patch(
        "inbox.views.reply."
        "send_email_task.delay"
    )
    def test_reply_all_excludes_self_and_bcc_and_preserves_roles(
        self,
        mocked_send_delay,
    ):
        self.inbound_message.sender_meta = {
            "name":
                "Customer",

            "email":
                "customer@example.com",
        }

        self.inbound_message.recipient_meta = {
            "to": [
                {
                    "name":
                        "",

                    "email":
                        "reply-user@oneuch.local",
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
                },
                {
                    "name":
                        "",

                    "email":
                        "reply-user@oneuch.local",
                },
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
        }

        self.inbound_message.save(
            update_fields=[
                "sender_meta",
                "recipient_meta",
            ]
        )


        self.client.force_authenticate(
            user=self.user
        )


        response = (
            self.client.post(
                self.url,
                {
                    "body":
                        "Reply all test",

                    "mode":
                        "reply_all",
                },
                format="json",
            )
        )


        self.assertEqual(
            response.status_code,
            202,
        )


        reply = (
            InboxMessage.objects.get(
                direction="outbound"
            )
        )


        self.assertEqual(
            [
                item[
                    "email"
                ]
                for item
                in reply
                .recipient_meta[
                    "to"
                ]
            ],
            [
                "support@example.com"
            ],
        )


        self.assertEqual(
            [
                item[
                    "email"
                ]
                for item
                in reply
                .recipient_meta[
                    "cc"
                ]
            ],
            [
                "lead@example.com",
                "finance@example.com",
            ],
        )


        self.assertEqual(
            reply.recipient_meta[
                "bcc"
            ],
            [],
        )


        self.assertNotIn(
            "reply-user@oneuch.local",
            reply.recipients,
        )

        self.assertNotIn(
            "hidden@example.com",
            reply.recipients,
        )


        mocked_send_delay.assert_called_once_with(
            self.email_account.id,
            "support@example.com",
            "Re: Customer requirement",
            "Reply all test",
            reply.id,
            "reply_all",
        )
