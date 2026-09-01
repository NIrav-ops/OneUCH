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

from django.core.files.uploadedfile import (
    SimpleUploadedFile,
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


User = get_user_model()


class OutboundAttachmentTests(
    APITestCase
):

    def setUp(
        self,
    ):
        self.user = (
            User.objects.create_user(
                email="attachment-user@oneuch.local",
                password="test-password-123",
            )
        )

        self.organization = (
            Organization.objects.create(
                name="Outbound Attachment Organization",
                slug="outbound-attachment-organization",
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
                email_address="attach@gmail.com",
                account_type="gmail",
                credential_status="active",
                is_active=True,
            )
        )

        self.outlook = (
            EmailAccount.objects.create(
                user=self.user,
                email_address="attach@outlook.com",
                account_type="outlook",
                credential_status="active",
                is_active=True,
            )
        )

        self.client.force_authenticate(
            user=self.user
        )


    def _base_payload(
        self,
        account,
    ):
        return {
            "to":
                "recipient@example.com",

            "cc":
                "",

            "bcc":
                "",

            "subject":
                "Outbound attachment test",

            "body":
                "Please see attached.",

            "account_id":
                str(
                    account.id
                ),
        }


    def _gmail_service(
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
                "gmail-attachment-sent"
        }

        return service


    def test_gmail_attachment_is_in_mime_and_local_metadata(
        self,
    ):
        service = (
            self._gmail_service()
        )

        upload = (
            SimpleUploadedFile(
                "proposal.pdf",
                b"pdf-content",
                content_type="application/pdf",
            )
        )

        payload = (
            self._base_payload(
                self.gmail
            )
        )

        payload[
            "attachments"
        ] = upload


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
                    payload,
                    format="multipart",
                )
            )


        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data[
                "attachment_count"
            ],
            1,
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


        attachment_parts = [
            part
            for part
            in mime.walk()
            if part.get_filename()
        ]


        self.assertEqual(
            len(
                attachment_parts
            ),
            1,
        )

        self.assertEqual(
            attachment_parts[
                0
            ].get_filename(),
            "proposal.pdf",
        )

        self.assertEqual(
            attachment_parts[
                0
            ].get_payload(
                decode=True
            ),
            b"pdf-content",
        )


        sent = (
            InboxMessage.objects.get(
                id=response.data[
                    "message_id"
                ]
            )
        )


        self.assertEqual(
            sent.attachment_meta[
                0
            ][
                "filename"
            ],
            "proposal.pdf",
        )

        self.assertIsNone(
            sent.attachment_meta[
                0
            ][
                "attachment_id"
            ]
        )


    def test_outlook_attachment_is_in_graph_payload(
        self,
    ):
        upload = (
            SimpleUploadedFile(
                "pricing.xlsx",
                b"xlsx-content",
                content_type=(
                    "application/"
                    "vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
            )
        )

        payload = (
            self._base_payload(
                self.outlook
            )
        )

        payload[
            "attachments"
        ] = upload


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
                "inbox.views.send_message.requests.post",
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
                    payload,
                    format="multipart",
                )
            )


        self.assertEqual(
            response.status_code,
            200,
        )


        graph_message = (
            mocked_post
            .call_args
            .kwargs[
                "json"
            ][
                "message"
            ]
        )


        attachments = (
            graph_message[
                "attachments"
            ]
        )


        self.assertEqual(
            len(
                attachments
            ),
            1,
        )

        self.assertEqual(
            attachments[
                0
            ][
                "name"
            ],
            "pricing.xlsx",
        )

        self.assertEqual(
            base64.b64decode(
                attachments[
                    0
                ][
                    "contentBytes"
                ]
            ),
            b"xlsx-content",
        )


    def test_outlook_oversize_attachment_is_rejected_before_provider_call(
        self,
    ):
        upload = (
            SimpleUploadedFile(
                "large.bin",
                (
                    b"x"
                    *
                    (
                        3
                        *
                        1024
                        *
                        1024
                        +
                        1
                    )
                ),
                content_type=(
                    "application/octet-stream"
                ),
            )
        )

        payload = (
            self._base_payload(
                self.outlook
            )
        )

        payload[
            "attachments"
        ] = upload


        with patch(
            "inbox.views.send_message.requests.post"
        ) as mocked_post:

            response = (
                self.client.post(
                    "/api/inbox/send/",
                    payload,
                    format="multipart",
                )
            )


        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "outbound limit",
            response.data[
                "error"
            ],
        )

        mocked_post.assert_not_called()


    def test_more_than_ten_attachments_is_rejected(
        self,
    ):
        files = [
            SimpleUploadedFile(
                f"file-{index}.txt",
                b"x",
                content_type="text/plain",
            )

            for index
            in range(
                11
            )
        ]


        payload = (
            self._base_payload(
                self.gmail
            )
        )

        payload[
            "attachments"
        ] = files


        with patch(
            "inbox.views.send_message.build"
        ) as mocked_build:

            response = (
                self.client.post(
                    "/api/inbox/send/",
                    payload,
                    format="multipart",
                )
            )


        self.assertEqual(
            response.status_code,
            400,
        )

        mocked_build.assert_not_called()


    def test_draft_save_persists_uploaded_file_instead_of_silent_loss(
        self,
    ):
        upload = (
            SimpleUploadedFile(
                "draft.pdf",
                b"draft-file",
                content_type="application/pdf",
            )
        )


        response = (
            self.client.post(
                "/api/inbox/draft/save/",
                {
                    "to":
                        "recipient@example.com",

                    "subject":
                        "Draft attachment",

                    "body":
                        "Body",

                    "account_id":
                        str(
                            self.gmail.id
                        ),

                    "attachments":
                        upload,
                },
                format="multipart",
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        self.assertEqual(
            response.data[
                "status"
            ],
            "draft_saved",
        )


        self.assertEqual(
            response.data[
                "attachment_count"
            ],
            1,
        )


        draft = (
            InboxMessage.objects
            .get(
                id=response.data[
                    "draft_id"
                ]
            )
        )


        self.assertTrue(
            draft.is_draft
        )


        self.assertEqual(
            draft.attachments.count(),
            1,
        )


        attachment = (
            draft.attachments.first()
        )


        self.assertEqual(
            attachment.filename,
            "draft.pdf",
        )


        self.assertEqual(
            attachment.content_type,
            "application/pdf",
        )


        attachment.file.open(
            "rb"
        )


        try:

            content = (
                attachment.file.read()
            )

        finally:

            attachment.file.close()


        self.assertEqual(
            content,
            b"draft-file",
        )


    def test_forward_can_send_user_added_attachment(
        self,
    ):
        conversation = (
            Conversation.objects.create(
                user=self.user,
                organization=self.organization,
                email_account=self.gmail,
                subject="Forward source",
                conversation_key="attachment-forward-source",
            )
        )


        source = (
            InboxMessage.objects.create(
                user=self.user,
                organization=self.organization,
                email_account=self.gmail,
                platform="gmail",
                folder="inbox",
                direction="inbound",
                conversation=conversation,
                external_message_id="gmail-source-id",
                external_conversation_id="gmail-thread-id",
                sender="customer@example.com",
                recipients=self.gmail.email_address,
                recipient_meta={
                    "to": [
                        {
                            "name":
                                "",

                            "email":
                                self.gmail.email_address,
                        }
                    ],

                    "cc":
                        [],

                    "bcc":
                        [],

                    "reply_to":
                        [],
                },
                subject="Forward source",
                body="Original body",
                received_at=timezone.now(),
                status="sent",
            )
        )


        upload = (
            SimpleUploadedFile(
                "added.txt",
                b"added-file-content",
                content_type="text/plain",
            )
        )


        service = (
            self._gmail_service()
        )


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
                    (
                        "/api/inbox/message/"
                        + str(
                            source.id
                        )
                        + "/forward/"
                    ),
                    {
                        "to":
                            "forward@example.com",

                        "body":
                            "Please review.",

                        "attachments":
                            upload,
                    },
                    format="multipart",
                )
            )


        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data[
                "attachment_count"
            ],
            1,
        )

        self.assertFalse(
            response.data[
                "attachments_forwarded"
            ]
        )

        # "attachments_forwarded" still means ORIGINAL source
        # attachments are not copied automatically. The new
        # file added by the user was delivered separately.
