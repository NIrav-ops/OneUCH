import base64

from email import (
    message_from_bytes,
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


User = get_user_model()


class OutboundSignatureTests(
    APITestCase
):

    def setUp(
        self,
    ):
        self.user = (
            User.objects.create_user(
                email="outbound-signature@oneuch.local",
                password="test-password-123",
            )
        )

        self.organization = (
            Organization.objects.create(
                name="Outbound Signature Organization",
                slug="outbound-signature-organization",
            )
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=self.organization,
            role="member",
        )

        self.gmail = (
            EmailAccount.objects.create(
                user=self.user,
                email_address="pilot@gmail.com",
                account_type="gmail",
                credential_status="active",
                is_active=True,
                signature_enabled=True,
                signature_text=(
                    "Kind regards,\n"
                    "Gmail Pilot"
                ),
            )
        )

        self.outlook = (
            EmailAccount.objects.create(
                user=self.user,
                email_address="pilot@outlook.com",
                account_type="outlook",
                credential_status="active",
                is_active=True,
                signature_enabled=True,
                signature_text=(
                    "Regards,\n"
                    "Microsoft Pilot"
                ),
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
                    "email":
                        "recipient@example.com",
                }
            ],

            "cc":
                [],

            "bcc":
                [],

            "subject":
                "Signature test",

            "body":
                "Hello from One UCH",

            "account_id":
                account.id,
        }


    def test_gmail_new_message_contains_signature_at_provider_and_locally(
        self,
    ):
        service = MagicMock()

        (
            service.users
            .return_value
            .messages
            .return_value
            .send
            .return_value
            .execute
            .return_value
        ) = {
            "id":
                "gmail-sent-id"
        }


        with (
            patch(
                "inbox.views.send_message."
                "get_gmail_credentials"
            ),
            patch(
                "inbox.views.send_message.build",
                return_value=service,
            ),
            patch(
                "inbox.views.send_message."
                "get_channel_layer"
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


        call = (
            service.users
            .return_value
            .messages
            .return_value
            .send
            .call_args
        )


        raw = (
            call.kwargs[
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


        provider_body = (
            mime.get_payload(
                decode=True
            )
            .decode(
                "utf-8"
            )
        )


        self.assertIn(
            "Hello from One UCH",
            provider_body,
        )

        self.assertIn(
            "Kind regards,\nGmail Pilot",
            provider_body,
        )

        self.assertEqual(
            provider_body.count(
                "Gmail Pilot"
            ),
            1,
        )


        sent = (
            InboxMessage.objects
            .get(
                id=response.data[
                    "message_id"
                ]
            )
        )


        self.assertIn(
            "Gmail Pilot",
            sent.body,
        )


    def test_outlook_new_message_contains_signature_at_provider_and_locally(
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
                return_value=graph_response,
            ) as mocked_post,
            patch(
                "inbox.views.send_message."
                "get_channel_layer"
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


        provider_body = (
            mocked_post
            .call_args
            .kwargs[
                "json"
            ][
                "message"
            ][
                "body"
            ][
                "content"
            ]
        )


        self.assertIn(
            "Hello from One UCH",
            provider_body,
        )

        self.assertIn(
            "Regards,\nMicrosoft Pilot",
            provider_body,
        )

        self.assertEqual(
            provider_body.count(
                "Microsoft Pilot"
            ),
            1,
        )


        sent = (
            InboxMessage.objects
            .get(
                id=response.data[
                    "message_id"
                ]
            )
        )


        self.assertIn(
            "Microsoft Pilot",
            sent.body,
        )


    def _inbound(
        self,
        account,
    ):
        conversation = (
            Conversation.objects.create(
                user=self.user,
                organization=self.organization,
                email_account=account,
                subject="Customer thread",
                conversation_key=(
                    "signature-thread-"
                    + str(account.id)
                ),
            )
        )


        message = (
            InboxMessage.objects.create(
                user=self.user,
                organization=self.organization,
                email_account=account,
                platform=account.account_type,
                folder="inbox",
                direction="inbound",
                conversation=conversation,
                external_message_id=(
                    "provider-message-"
                    + str(account.id)
                ),
                external_conversation_id=(
                    "provider-thread-"
                    + str(account.id)
                ),
                sender="customer@example.com",
                sender_meta={
                    "name":
                        "Customer",

                    "email":
                        "customer@example.com",
                },
                recipients=account.email_address,
                recipient_meta={
                    "to": [
                        {
                            "name":
                                "",

                            "email":
                                account.email_address,
                        }
                    ],

                    "cc":
                        [],

                    "bcc":
                        [],

                    "reply_to":
                        [],
                },
                subject="Customer thread",
                body="Incoming body",
                received_at=timezone.now(),
                is_read=True,
                status="sent",
            )
        )


        conversation.last_message = (
            message
        )

        conversation.last_message_at = (
            message.received_at
        )

        conversation.save(
            update_fields=[
                "last_message",
                "last_message_at",
            ]
        )


        return (
            conversation,
            message,
        )


    def test_reply_queues_body_with_mailbox_signature(
        self,
    ):
        conversation, _ = (
            self._inbound(
                self.gmail
            )
        )


        with patch(
            "inbox.views.reply."
            "send_email_task.delay"
        ) as queued:

            response = (
                self.client.post(
                    (
                        "/api/inbox/conversations/"
                        + str(
                            conversation.id
                        )
                        + "/reply/"
                    ),
                    {
                        "body":
                            "Thanks for the update.",

                        "mode":
                            "reply",
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
                id=response.data[
                    "message_id"
                ]
            )
        )


        self.assertIn(
            "Thanks for the update.",
            reply.body,
        )

        self.assertIn(
            "Gmail Pilot",
            reply.body,
        )

        self.assertEqual(
            reply.body.count(
                "Gmail Pilot"
            ),
            1,
        )


        queued_body = (
            queued
            .call_args
            .args[
                3
            ]
        )


        self.assertEqual(
            queued_body,
            reply.body,
        )


    def test_forward_places_signature_before_forwarded_content_once(
        self,
    ):
        _, source = (
            self._inbound(
                self.gmail
            )
        )


        mocked_response = (
            Response(
                {
                    "status":
                        "sent",

                    "conversation_id":
                        source.conversation_id,

                    "message_id":
                        999,
                },
                status=200,
            )
        )


        with patch(
            "inbox.views.forward."
            "UnifiedSendMessageAPIView."
            "send_with_data",
            return_value=mocked_response,
        ) as mocked_send:

            response = (
                self.client.post(
                    (
                        "/api/inbox/message/"
                        + str(
                            source.id
                        )
                        + "/forward/"
                    ),
                    {
                        "to": [
                            {
                                "email":
                                    "forward@example.com",
                            }
                        ],

                        "body":
                            "Please review.",
                    },
                    format="json",
                )
            )


        self.assertEqual(
            response.status_code,
            200,
        )


        kwargs = (
            mocked_send
            .call_args
            .kwargs
        )


        body = (
            kwargs[
                "data"
            ][
                "body"
            ]
        )


        signature_index = (
            body.index(
                "Gmail Pilot"
            )
        )

        forwarded_index = (
            body.index(
                "---------- Forwarded message ----------"
            )
        )


        self.assertLess(
            signature_index,
            forwarded_index,
        )

        self.assertEqual(
            body.count(
                "Gmail Pilot"
            ),
            1,
        )

        self.assertTrue(
            kwargs[
                "signature_already_applied"
            ]
        )
