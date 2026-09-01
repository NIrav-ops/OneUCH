import base64

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


class MailExperienceTests(
    APITestCase
):

    def setUp(
        self,
    ):
        self.user = (
            User.objects.create_user(
                email=(
                    "p3c-user@oneuch.test"
                ),
                password="pass123",
            )
        )


        self.organization = (
            Organization.objects.create(
                name="P3C Organization",
                slug="p3c-organization",
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
                    "p3c-user@gmail.test"
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
                    "P3C customer message"
                ),
                conversation_key=(
                    "p3c-conversation"
                ),
                external_conversation_id=(
                    "gmail-thread-123"
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
                conversation=(
                    self.conversation
                ),
                platform="gmail",
                folder="inbox",
                direction="inbound",
                external_message_id=(
                    "gmail-message-123"
                ),
                external_conversation_id=(
                    "gmail-thread-123"
                ),
                sender=(
                    "customer@example.com"
                ),
                recipients=(
                    "p3c-user@gmail.test"
                ),
                recipient_meta={
                    "to": [
                        {
                            "name":
                                "",

                            "email":
                                "p3c-user@gmail.test",
                        }
                    ],

                    "cc": [
                        {
                            "name":
                                "Finance",

                            "email":
                                "finance@example.com",
                        }
                    ],

                    "bcc":
                        [],

                    "reply_to":
                        [],
                },
                subject=(
                    "P3C customer message"
                ),
                body=(
                    "Original message body"
                ),
                attachment_meta=[
                    {
                        "filename":
                            "proposal.pdf",

                        "attachment_id":
                            "gmail-att-1",

                        "mime_type":
                            "application/pdf",
                    }
                ],
                received_at=(
                    timezone.now()
                ),
                status="sent",
            )
        )


    def test_provider_open_requires_authentication(
        self,
    ):
        response = (
            self.client.get(
                (
                    "/api/inbox/message/"
                    + str(
                        self.message.id
                    )
                    + "/provider-open/"
                )
            )
        )


        self.assertIn(
            response.status_code,
            {
                401,
                403,
            },
        )


    def test_gmail_provider_open_is_user_scoped_and_thread_based(
        self,
    ):
        self.client.force_authenticate(
            user=self.user
        )


        response = (
            self.client.get(
                (
                    "/api/inbox/message/"
                    + str(
                        self.message.id
                    )
                    + "/provider-open/"
                )
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        self.assertEqual(
            response.data[
                "provider"
            ],
            "gmail",
        )


        self.assertIn(
            "mail.google.com",
            response.data[
                "url"
            ],
        )


        self.assertIn(
            "gmail-thread-123",
            response.data[
                "url"
            ],
        )


    def test_outlook_provider_open_uses_provider_message_id(
        self,
    ):
        outlook = (
            EmailAccount.objects.create(
                user=self.user,
                email_address=(
                    "p3c-user@outlook.test"
                ),
                account_type="outlook",
                credential_status="active",
                is_active=True,
            )
        )


        conversation = (
            Conversation.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                email_account=(
                    outlook
                ),
                subject="Outlook",
                conversation_key=(
                    "p3c-outlook"
                ),
                external_conversation_id=(
                    "graph-thread"
                ),
            )
        )


        message = (
            InboxMessage.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                email_account=(
                    outlook
                ),
                conversation=(
                    conversation
                ),
                platform="outlook",
                folder="inbox",
                direction="inbound",
                external_message_id=(
                    "graph/message+id="
                ),
                external_conversation_id=(
                    "graph-thread"
                ),
                sender=(
                    "customer@example.com"
                ),
                recipients=(
                    outlook.email_address
                ),
                subject="Outlook",
                body="Body",
                received_at=(
                    timezone.now()
                ),
                status="sent",
            )
        )


        self.client.force_authenticate(
            user=self.user
        )


        response = (
            self.client.get(
                (
                    "/api/inbox/message/"
                    + str(
                        message.id
                    )
                    + "/provider-open/"
                )
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        self.assertIn(
            "outlook.office.com",
            response.data[
                "url"
            ],
        )


        self.assertNotIn(
            "/message+id=",
            response.data[
                "url"
            ],
        )


    @patch(
        "inbox.views.forward."
        "UnifiedSendMessageAPIView."
        "send_with_data"
    )
    def test_forward_uses_source_mailbox_and_materializes_forwarded_content(
        self,
        mocked_send,
    ):
        mocked_send.return_value = (
            Response(
                {
                    "status":
                        "sent"
                },
                status=200,
            )
        )


        self.client.force_authenticate(
            user=self.user
        )


        response = (
            self.client.post(
                (
                    "/api/inbox/message/"
                    + str(
                        self.message.id
                    )
                    + "/forward/"
                ),
                {
                    "to": [
                        {
                            "name":
                                "New Recipient",

                            "email":
                                "new@example.com",
                        }
                    ],

                    "cc":
                        [],

                    "bcc":
                        [],

                    "subject":
                        "Fwd: P3C customer message",

                    "body":
                        "FYI",

                    "source_attachment_keys":
                        [],
                },
                format="json",
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        mocked_send.assert_called_once()


        payload = (
            mocked_send
            .call_args
            .kwargs[
                "data"
            ]
        )


        self.assertEqual(
            payload[
                "account_id"
            ],
            self.account.id,
        )


        self.assertEqual(
            payload[
                "subject"
            ],
            "Fwd: P3C customer message",
        )


        self.assertIn(
            "FYI",
            payload[
                "body"
            ],
        )


        self.assertIn(
            "---------- Forwarded message ----------",
            payload[
                "body"
            ],
        )


        self.assertIn(
            "Original message body",
            payload[
                "body"
            ],
        )


        self.assertFalse(
            response.data[
                "attachments_forwarded"
            ]
        )


        self.assertEqual(
            response.data[
                "source_attachment_count"
            ],
            1,
        )


    @patch(
        "inbox.views_attachment.build"
    )
    @patch(
        "inbox.views_attachment."
        "get_gmail_credentials"
    )
    def test_known_gmail_attachment_download_uses_validated_metadata(
        self,
        mocked_credentials,
        mocked_build,
    ):
        service = (
            MagicMock()
        )


        (
            service.users
            .return_value
            .messages
            .return_value
            .attachments
            .return_value
            .get
            .return_value
            .execute
            .return_value
        ) = {
            "data":
                base64
                .urlsafe_b64encode(
                    b"attachment-data"
                )
                .decode()
        }


        mocked_build.return_value = (
            service
        )


        self.client.force_authenticate(
            user=self.user
        )


        response = (
            self.client.get(
                (
                    "/api/inbox/attachments/"
                    + str(
                        self.message.id
                    )
                    + "/gmail-att-1/"
                )
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        self.assertEqual(
            response.content,
            b"attachment-data",
        )


        self.assertIn(
            "proposal.pdf",
            response[
                "Content-Disposition"
            ],
        )


    @patch(
        "inbox.views_attachment.build"
    )
    def test_unknown_attachment_id_is_rejected_before_provider_fetch(
        self,
        mocked_build,
    ):
        self.client.force_authenticate(
            user=self.user
        )


        response = (
            self.client.get(
                (
                    "/api/inbox/attachments/"
                    + str(
                        self.message.id
                    )
                    + "/attacker-controlled-id/"
                )
            )
        )


        self.assertEqual(
            response.status_code,
            404,
        )


        mocked_build.assert_not_called()


    def test_conversation_detail_exposes_downloadable_attachment_capability(
        self,
    ):
        self.client.force_authenticate(
            user=self.user
        )


        response = (
            self.client.get(
                (
                    "/api/inbox/conversations/"
                    + str(
                        self.conversation.id
                    )
                    + "/"
                )
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        self.assertEqual(
            response.data[
                "attachments"
            ][0][
                "downloadable"
            ],
            True,
        )
