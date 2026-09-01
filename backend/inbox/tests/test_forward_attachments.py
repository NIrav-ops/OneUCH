import base64
import json
import shutil
import tempfile

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

from django.test import (
    override_settings,
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

from inbox.services.persistent_outbound_attachments import (
    persist_outbound_attachments,
)


class ForwardOriginalAttachmentTests(
    APITestCase
):

    def setUp(
        self,
    ):

        self.media_root = (
            tempfile.mkdtemp()
        )


        self.media_override = (
            override_settings(
                MEDIA_ROOT=(
                    self.media_root
                )
            )
        )


        self.media_override.enable()


        self.addCleanup(
            self.media_override.disable
        )


        self.addCleanup(
            shutil.rmtree,
            self.media_root,
            True,
        )


        User = (
            get_user_model()
        )


        self.user = (
            User.objects.create_user(
                email=(
                    "forward-files"
                    "@oneuch.local"
                ),
                password=(
                    "test-password-123"
                ),
            )
        )


        self.organization = (
            Organization.objects.create(
                name=(
                    "Forward File Organization"
                ),
                slug=(
                    "forward-file-organization"
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


        self.gmail = (
            EmailAccount.objects.create(
                user=self.user,
                email_address=(
                    "forward-gmail"
                    "@oneuch.local"
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
                    "forward-outlook"
                    "@oneuch.local"
                ),
                account_type="outlook",
                credential_status="active",
                is_active=True,
            )
        )


        self.client.force_authenticate(
            user=self.user
        )


    def make_source(
        self,
        *,
        account=None,
        platform=None,
        attachment_meta=None,
        recipient_meta=None,
        key="forward-source",
    ):

        account = (
            account
            or
            self.gmail
        )


        platform = (
            platform
            or
            account.account_type
        )


        conversation = (
            Conversation.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                email_account=(
                    account
                ),
                subject=(
                    "Original forward source"
                ),
                conversation_key=key,
                external_conversation_id=(
                    "thread-"
                    +
                    key
                ),
            )
        )


        return (
            InboxMessage.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                email_account=(
                    account
                ),
                conversation=(
                    conversation
                ),
                platform=platform,
                folder="inbox",
                direction="inbound",
                external_message_id=(
                    "provider-message-"
                    +
                    key
                ),
                external_conversation_id=(
                    "thread-"
                    +
                    key
                ),
                sender=(
                    "customer@example.com"
                ),
                recipients=(
                    account.email_address
                ),
                recipient_meta=(
                    recipient_meta
                    or
                    {
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
                    }
                ),
                subject=(
                    "Original forward source"
                ),
                body=(
                    "Original body"
                ),
                attachment_meta=(
                    attachment_meta
                    or []
                ),
                received_at=(
                    timezone.now()
                ),
                status="sent",
            )
        )


    def fake_send(
        self,
        *args,
        **kwargs,
    ):

        prepared = (
            kwargs.get(
                "prepared_attachments"
            )
            or []
        )


        return Response(
            {
                "status":
                    "sent",

                "message_id":
                    999,

                "conversation_id":
                    999,

                "attachment_count":
                    len(
                        prepared
                    ),
            },
            status=200,
        )


    def test_forward_preflight_lists_original_attachment_by_default(
        self,
    ):

        source = (
            self.make_source(
                attachment_meta=[
                    {
                        "filename":
                            "proposal.pdf",

                        "attachment_id":
                            "gmail-att-1",

                        "mime_type":
                            "application/pdf",

                        "size":
                            1234,
                    }
                ],
            )
        )


        response = (
            self.client.get(
                (
                    "/api/inbox/message/"
                    +
                    str(
                        source.id
                    )
                    +
                    "/forward/"
                )
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        self.assertEqual(
            response.data[
                "source_attachment_count"
            ],
            1,
        )


        self.assertTrue(
            response.data[
                "attachments_forwarded_by_default"
            ]
        )


        item = (
            response.data[
                "source_attachments"
            ][0]
        )


        self.assertEqual(
            item[
                "key"
            ],
            "provider:gmail-att-1",
        )


        self.assertEqual(
            item[
                "filename"
            ],
            "proposal.pdf",
        )


        self.assertTrue(
            item[
                "selected"
            ]
        )


    @patch(
        "inbox.views.forward."
        "UnifiedSendMessageAPIView."
        "send_with_data"
    )
    @patch(
        "inbox.services.forward_attachments."
        "build"
    )
    @patch(
        "inbox.services.forward_attachments."
        "get_gmail_credentials"
    )
    def test_gmail_forward_auto_includes_original_plus_user_file(
        self,
        mocked_credentials,
        mocked_build,
        mocked_send,
    ):

        source_bytes = (
            b"original-gmail-bytes"
        )


        source = (
            self.make_source(
                attachment_meta=[
                    {
                        "filename":
                            "original.txt",

                        "attachment_id":
                            "gmail-original-id",

                        "mime_type":
                            "text/plain",

                        "size":
                            len(
                                source_bytes
                            ),
                    }
                ],
                key=(
                    "gmail-auto-original"
                ),
            )
        )


        service = MagicMock()


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
                    source_bytes
                )
                .decode()
        }


        mocked_build.return_value = (
            service
        )


        mocked_send.side_effect = (
            self.fake_send
        )


        added_bytes = (
            b"user-added-bytes"
        )


        response = (
            self.client.post(
                (
                    "/api/inbox/message/"
                    +
                    str(
                        source.id
                    )
                    +
                    "/forward/"
                ),
                {
                    "to":
                        "forward@example.com",

                    "body":
                        "Please review.",

                    # No source_attachment_keys field:
                    # all originals must be included by default.
                    "attachments":
                        SimpleUploadedFile(
                            "added.txt",
                            added_bytes,
                            content_type=(
                                "text/plain"
                            ),
                        ),
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
                "source_attachment_count"
            ],
            1,
        )


        self.assertEqual(
            response.data[
                "source_attachments_forwarded"
            ],
            1,
        )


        self.assertEqual(
            response.data[
                "user_attachment_count"
            ],
            1,
        )


        self.assertTrue(
            response.data[
                "attachments_forwarded"
            ]
        )


        prepared = (
            mocked_send
            .call_args
            .kwargs[
                "prepared_attachments"
            ]
        )


        self.assertEqual(
            len(
                prepared
            ),
            2,
        )


        self.assertEqual(
            prepared[0][
                "filename"
            ],
            "original.txt",
        )


        self.assertEqual(
            prepared[0][
                "content"
            ],
            source_bytes,
        )


        self.assertTrue(
            prepared[0][
                "forwarded_original"
            ]
        )


        self.assertEqual(
            prepared[1][
                "filename"
            ],
            "added.txt",
        )


        self.assertEqual(
            prepared[1][
                "content"
            ],
            added_bytes,
        )


    @patch(
        "inbox.views.forward."
        "UnifiedSendMessageAPIView."
        "send_with_data"
    )
    @patch(
        "inbox.services.forward_attachments."
        "build"
    )
    def test_user_can_remove_all_original_attachments(
        self,
        mocked_build,
        mocked_send,
    ):

        source = (
            self.make_source(
                attachment_meta=[
                    {
                        "filename":
                            "remove-me.txt",

                        "attachment_id":
                            "remove-provider-id",

                        "mime_type":
                            "text/plain",
                    }
                ],
                key=(
                    "remove-all-originals"
                ),
            )
        )


        mocked_send.side_effect = (
            self.fake_send
        )


        response = (
            self.client.post(
                (
                    "/api/inbox/message/"
                    +
                    str(
                        source.id
                    )
                    +
                    "/forward/"
                ),
                {
                    "to":
                        "forward@example.com",

                    "body":
                        "No inherited files.",

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


        self.assertEqual(
            response.data[
                "source_attachment_count"
            ],
            1,
        )


        self.assertEqual(
            response.data[
                "source_attachments_forwarded"
            ],
            0,
        )


        self.assertFalse(
            response.data[
                "attachments_forwarded"
            ]
        )


        self.assertEqual(
            mocked_send
            .call_args
            .kwargs[
                "prepared_attachments"
            ],
            [],
        )


        mocked_build.assert_not_called()


    @patch(
        "inbox.views.forward."
        "UnifiedSendMessageAPIView."
        "send_with_data"
    )
    @patch(
        "inbox.services.forward_attachments."
        "build"
    )
    def test_tampered_provider_attachment_key_is_rejected_before_fetch(
        self,
        mocked_build,
        mocked_send,
    ):

        source = (
            self.make_source(
                attachment_meta=[
                    {
                        "filename":
                            "valid.txt",

                        "attachment_id":
                            "valid-provider-id",

                        "mime_type":
                            "text/plain",
                    }
                ],
                key=(
                    "tampered-provider-id"
                ),
            )
        )


        response = (
            self.client.post(
                (
                    "/api/inbox/message/"
                    +
                    str(
                        source.id
                    )
                    +
                    "/forward/"
                ),
                {
                    "to":
                        "forward@example.com",

                    "body":
                        "Attempt",

                    "source_attachment_keys":
                        [
                            "provider:attacker-id"
                        ],
                },
                format="json",
            )
        )


        self.assertEqual(
            response.status_code,
            400,
        )


        self.assertIn(
            "does not belong",
            response.data[
                "error"
            ],
        )


        mocked_build.assert_not_called()

        mocked_send.assert_not_called()


    @patch(
        "inbox.views.forward."
        "UnifiedSendMessageAPIView."
        "send_with_data"
    )
    @patch(
        "inbox.services.forward_attachments."
        "requests.get"
    )
    @patch(
        "inbox.services.forward_attachments."
        "get_microsoft_access_token"
    )
    def test_microsoft_original_attachment_is_fetched_and_forwarded(
        self,
        mocked_token,
        mocked_get,
        mocked_send,
    ):

        source_bytes = (
            b"original-microsoft-bytes"
        )


        source = (
            self.make_source(
                account=self.outlook,
                platform="outlook",
                attachment_meta=[
                    {
                        "filename":
                            "graph.txt",

                        "attachment_id":
                            "graph-att-id",

                        "mime_type":
                            "text/plain",

                        "size":
                            len(
                                source_bytes
                            ),
                    }
                ],
                key=(
                    "microsoft-original"
                ),
            )
        )


        mocked_token.return_value = (
            "token"
        )


        graph_response = MagicMock()

        graph_response.status_code = (
            200
        )


        graph_response.json.return_value = {
            "contentBytes":
                base64.b64encode(
                    source_bytes
                )
                .decode()
        }


        mocked_get.return_value = (
            graph_response
        )


        mocked_send.side_effect = (
            self.fake_send
        )


        response = (
            self.client.post(
                (
                    "/api/inbox/message/"
                    +
                    str(
                        source.id
                    )
                    +
                    "/forward/"
                ),
                {
                    "to":
                        "forward@example.com",

                    "body":
                        "Graph forward",
                },
                format="json",
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        prepared = (
            mocked_send
            .call_args
            .kwargs[
                "prepared_attachments"
            ]
        )


        self.assertEqual(
            len(
                prepared
            ),
            1,
        )


        self.assertEqual(
            prepared[0][
                "content"
            ],
            source_bytes,
        )


        self.assertEqual(
            prepared[0][
                "filename"
            ],
            "graph.txt",
        )


    @patch(
        "inbox.views.forward."
        "UnifiedSendMessageAPIView."
        "send_with_data"
    )
    @patch(
        "inbox.services.forward_attachments."
        "build"
    )
    def test_local_durable_source_attachment_avoids_provider_download(
        self,
        mocked_build,
        mocked_send,
    ):

        source = (
            self.make_source(
                attachment_meta=[
                    {
                        "filename":
                            "local.txt",

                        "attachment_id":
                            None,

                        "mime_type":
                            "text/plain",
                    }
                ],
                key=(
                    "local-durable"
                ),
            )
        )


        local_bytes = (
            b"oneuch-owned-source-bytes"
        )


        records = (
            persist_outbound_attachments(
                message=source,
                prepared=[
                    {
                        "filename":
                            "local.txt",

                        "content_type":
                            "text/plain",

                        "size":
                            len(
                                local_bytes
                            ),

                        "content":
                            local_bytes,
                    }
                ],
            )
        )


        mocked_send.side_effect = (
            self.fake_send
        )


        preflight = (
            self.client.get(
                (
                    "/api/inbox/message/"
                    +
                    str(
                        source.id
                    )
                    +
                    "/forward/"
                )
            )
        )


        self.assertEqual(
            preflight.status_code,
            200,
        )


        self.assertEqual(
            preflight.data[
                "source_attachments"
            ][0][
                "key"
            ],
            (
                "local:"
                +
                str(
                    records[0].id
                )
            ),
        )


        response = (
            self.client.post(
                (
                    "/api/inbox/message/"
                    +
                    str(
                        source.id
                    )
                    +
                    "/forward/"
                ),
                {
                    "to":
                        "forward@example.com",

                    "body":
                        "Local source",
                },
                format="json",
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        prepared = (
            mocked_send
            .call_args
            .kwargs[
                "prepared_attachments"
            ]
        )


        self.assertEqual(
            prepared[0][
                "content"
            ],
            local_bytes,
        )


        self.assertEqual(
            prepared[0][
                "source_attachment_key"
            ],
            (
                "local:"
                +
                str(
                    records[0].id
                )
            ),
        )


        mocked_build.assert_not_called()


    @patch(
        "inbox.views.forward."
        "UnifiedSendMessageAPIView."
        "send_with_data"
    )
    def test_source_bcc_is_never_materialized_in_forwarded_body(
        self,
        mocked_send,
    ):

        secret = (
            "secret-bcc@example.com"
        )


        source = (
            self.make_source(
                recipient_meta={
                    "to": [
                        {
                            "name":
                                "",

                            "email":
                                self.gmail.email_address,
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

                    "bcc": [
                        {
                            "name":
                                "Hidden",

                            "email":
                                secret,
                        }
                    ],

                    "reply_to":
                        [],
                },
                key=(
                    "source-bcc-privacy"
                ),
            )
        )


        # Deliberately simulate the modern compatibility field,
        # which may contain flattened To + Cc + Bcc addresses.
        # Forwarded quoted headers must ignore this field.
        source.recipients = (
            self.gmail.email_address
            +
            ", finance@example.com, "
            +
            secret
        )

        source.save(
            update_fields=[
                "recipients"
            ]
        )


        mocked_send.side_effect = (
            self.fake_send
        )


        response = (
            self.client.post(
                (
                    "/api/inbox/message/"
                    +
                    str(
                        source.id
                    )
                    +
                    "/forward/"
                ),
                {
                    "to":
                        "new@example.com",

                    "body":
                        "FYI",
                },
                format="json",
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        payload = (
            mocked_send
            .call_args
            .kwargs[
                "data"
            ]
        )


        self.assertIn(
            "finance@example.com",
            payload[
                "body"
            ],
        )


        self.assertNotIn(
            secret,
            payload[
                "body"
            ],
        )


    @patch(
        "inbox.views.forward."
        "UnifiedSendMessageAPIView."
        "send_with_data"
    )
    @patch(
        "inbox.services.forward_attachments."
        "build"
    )
    def test_combined_source_plus_user_count_rejected_before_provider_fetch(
        self,
        mocked_build,
        mocked_send,
    ):

        source = (
            self.make_source(
                attachment_meta=[
                    {
                        "filename":
                            f"source-{index}.txt",

                        "attachment_id":
                            f"source-id-{index}",

                        "mime_type":
                            "text/plain",

                        "size":
                            1,
                    }

                    for index
                    in range(
                        10
                    )
                ],
                key=(
                    "combined-count-policy"
                ),
            )
        )


        response = (
            self.client.post(
                (
                    "/api/inbox/message/"
                    +
                    str(
                        source.id
                    )
                    +
                    "/forward/"
                ),
                {
                    "to":
                        "forward@example.com",

                    "body":
                        "Too many files",

                    "attachments":
                        SimpleUploadedFile(
                            "added.txt",
                            b"x",
                            content_type=(
                                "text/plain"
                            ),
                        ),
                },
                format="multipart",
            )
        )


        self.assertEqual(
            response.status_code,
            400,
        )


        self.assertIn(
            "maximum of 10",
            response.data[
                "error"
            ],
        )


        mocked_build.assert_not_called()

        mocked_send.assert_not_called()
