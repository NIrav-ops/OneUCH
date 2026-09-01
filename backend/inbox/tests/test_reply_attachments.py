import base64
import shutil
import tempfile

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

from django.test import (
    SimpleTestCase,
    TestCase,
    override_settings,
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

from email_accounts.services.gmail_api import (
    send_gmail_reply,
)

from email_accounts.services.microsoft_api import (
    send_outlook_reply,
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

from inbox.tasks import (
    send_email_task,
)


class ReplyAttachmentAPITests(
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


        User = get_user_model()


        self.user = (
            User.objects.create_user(
                email=(
                    "reply-attachment-user"
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
                    "Reply Attachment Organization"
                ),
                slug=(
                    "reply-attachment-organization"
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
                    "reply-attachment-user"
                    "@oneuch.local"
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
                    "Attachment requirement"
                ),
                conversation_key=(
                    "reply-attachment-conversation"
                ),
                external_conversation_id=(
                    "thread-attachment-1"
                ),
            )
        )


        self.inbound = (
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
                    "provider-message-attachment-1"
                ),
                external_conversation_id=(
                    "thread-attachment-1"
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
                    self.account.email_address
                ),
                recipient_meta={
                    "to": [
                        {
                            "name":
                                "",

                            "email":
                                self.account.email_address,
                        }
                    ],

                    "cc":
                        [],

                    "bcc":
                        [],

                    "reply_to":
                        [],
                },
                subject=(
                    "Attachment requirement"
                ),
                body=(
                    "Please reply with the document."
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
            +
            str(
                self.conversation.id
            )
            +
            "/reply/"
        )


        self.client.force_authenticate(
            user=self.user
        )


    @patch(
        "inbox.views.reply."
        "send_email_task.delay"
    )
    def test_reply_attachment_is_persisted_before_queue(
        self,
        mocked_delay,
    ):
        payload = (
            b"one-uch-reply-proof"
        )


        response = (
            self.client.post(
                self.url,
                {
                    "body":
                        "Attached as requested.",

                    "mode":
                        "reply",

                    "attachments":
                        SimpleUploadedFile(
                            "proof.txt",
                            payload,
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
            202,
        )

        self.assertEqual(
            response.data[
                "attachment_count"
            ],
            1,
        )


        reply = (
            InboxMessage.objects
            .get(
                id=response.data[
                    "message_id"
                ]
            )
        )


        self.assertEqual(
            reply.attachments.count(),
            1,
        )

        self.assertEqual(
            reply.attachment_meta[0][
                "filename"
            ],
            "proof.txt",
        )


        attachment = (
            reply.attachments.first()
        )


        attachment.file.open(
            "rb"
        )

        try:

            actual = (
                attachment.file.read()
            )

        finally:

            attachment.file.close()


        self.assertEqual(
            actual,
            payload,
        )


        mocked_delay.assert_called_once()


    @patch(
        "inbox.views.reply."
        "send_email_task.delay"
    )
    def test_reply_rejects_more_than_ten_files(
        self,
        mocked_delay,
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


        response = (
            self.client.post(
                self.url,
                {
                    "body":
                        "Too many attachments",

                    "mode":
                        "reply",

                    "attachments":
                        files,
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


        self.assertFalse(
            InboxMessage.objects
            .filter(
                conversation=(
                    self.conversation
                ),
                direction="outbound",
            )
            .exists()
        )


        mocked_delay.assert_not_called()


class ReplyAttachmentDeliveryTests(
    TestCase
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


        User = get_user_model()

        self.user = (
            User.objects.create_user(
                email=(
                    "reply-delivery-attachment"
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
                    "Reply Delivery Attachment Org"
                ),
                slug=(
                    "reply-delivery-attachment-org"
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
                    "reply-delivery-attachment"
                    "@oneuch.local"
                ),
                account_type="gmail",
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
                    self.account
                ),
                subject="Reply delivery",
                conversation_key=(
                    "reply-delivery-attachment"
                ),
                external_conversation_id=(
                    "gmail-thread"
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
                platform="gmail",
                direction="outbound",
                folder="outbox",
                conversation=(
                    conversation
                ),
                external_message_id="pending",
                external_conversation_id=(
                    "gmail-thread"
                ),
                in_reply_to=(
                    "gmail-original"
                ),
                sender=(
                    self.account.email_address
                ),
                recipients=(
                    "customer@example.com"
                ),
                recipient_meta={
                    "to": [
                        {
                            "name":
                                "",

                            "email":
                                "customer@example.com",
                        }
                    ],

                    "cc":
                        [],

                    "bcc":
                        [],

                    "reply_to":
                        [],
                },
                subject="Re: Reply delivery",
                body="Attached",
                received_at=(
                    timezone.now()
                ),
                status="queued",
            )
        )


        persist_outbound_attachments(
            message=self.message,
            prepared=[
                {
                    "filename":
                        "task-proof.txt",

                    "content_type":
                        "text/plain",

                    "size":
                        len(
                            b"task-proof"
                        ),

                    "content":
                        b"task-proof",
                }
            ],
        )


    @patch(
        "inbox.tasks.send_gmail_reply"
    )
    def test_celery_rehydrates_persisted_reply_attachment(
        self,
        mocked_send,
    ):
        mocked_send.return_value = {
            "id":
                "gmail-sent-with-file"
        }


        send_email_task.run(
            self.account.id,
            "customer@example.com",
            "Re: Reply delivery",
            "Attached",
            self.message.id,
        )


        kwargs = (
            mocked_send
            .call_args
            .kwargs
        )


        self.assertIn(
            "attachments",
            kwargs,
        )

        self.assertEqual(
            len(
                kwargs[
                    "attachments"
                ]
            ),
            1,
        )

        self.assertEqual(
            kwargs[
                "attachments"
            ][0][
                "filename"
            ],
            "task-proof.txt",
        )

        self.assertEqual(
            kwargs[
                "attachments"
            ][0][
                "content"
            ],
            b"task-proof",
        )


        self.message.refresh_from_db()


        self.assertEqual(
            self.message.status,
            "sent",
        )


class ReplyAttachmentProviderTests(
    SimpleTestCase
):

    @patch(
        "email_accounts.services.gmail_api."
        "requests.post"
    )
    @patch(
        "email_accounts.services.gmail_api."
        "requests.get"
    )
    @patch(
        "email_accounts.services.gmail_api."
        "get_valid_oauth_token"
    )
    def test_gmail_reply_builds_threaded_mime_attachment(
        self,
        mocked_token,
        mocked_get,
        mocked_post,
    ):
        token = MagicMock()

        token.access_token = (
            "google-token"
        )

        mocked_token.return_value = (
            token
        )


        metadata = MagicMock()

        metadata.status_code = 200

        metadata.json.return_value = {
            "payload": {
                "headers": [
                    {
                        "name":
                            "Message-ID",

                        "value":
                            "<original@example.com>",
                    }
                ]
            }
        }

        mocked_get.return_value = (
            metadata
        )


        sent = MagicMock()

        sent.status_code = 200

        sent.json.return_value = {
            "id":
                "gmail-with-attachment"
        }

        mocked_post.return_value = (
            sent
        )


        send_gmail_reply(
            user=object(),
            to_email=(
                "customer@example.com"
            ),
            subject="Re: Proof",
            body="Reply body",
            thread_id="gmail-thread",
            reply_to_message_id=(
                "gmail-original"
            ),
            attachments=[
                {
                    "filename":
                        "proof.txt",

                    "content_type":
                        "text/plain",

                    "size":
                        5,

                    "content":
                        b"proof",
                }
            ],
        )


        provider_body = (
            mocked_post
            .call_args
            .kwargs[
                "json"
            ]
        )


        self.assertEqual(
            provider_body[
                "threadId"
            ],
            "gmail-thread",
        )


        mime = (
            message_from_bytes(
                base64
                .urlsafe_b64decode(
                    provider_body[
                        "raw"
                    ]
                    .encode()
                )
            )
        )


        self.assertTrue(
            mime.is_multipart()
        )

        self.assertEqual(
            mime[
                "In-Reply-To"
            ],
            "<original@example.com>",
        )


        matching = [
            part
            for part
            in mime.walk()
            if part.get_filename()
            ==
            "proof.txt"
        ]


        self.assertEqual(
            len(
                matching
            ),
            1,
        )

        self.assertEqual(
            matching[0]
            .get_payload(
                decode=True
            ),
            b"proof",
        )


    @patch(
        "email_accounts.services.microsoft_api."
        "requests.delete"
    )
    @patch(
        "email_accounts.services.microsoft_api."
        "requests.post"
    )
    @patch(
        "email_accounts.services.microsoft_api."
        "get_valid_oauth_token"
    )
    def test_outlook_reply_attachment_uses_reply_draft_pipeline(
        self,
        mocked_token,
        mocked_post,
        mocked_delete,
    ):
        token = MagicMock()

        token.access_token = (
            "microsoft-token"
        )

        mocked_token.return_value = (
            token
        )


        created = MagicMock()

        created.status_code = 201

        created.json.return_value = {
            "id":
                "reply-draft-1"
        }


        attached = MagicMock()

        attached.status_code = 201


        sent = MagicMock()

        sent.status_code = 202


        mocked_post.side_effect = [
            created,
            attached,
            sent,
        ]


        result = (
            send_outlook_reply(
                user=object(),
                to_email=(
                    "customer@example.com"
                ),
                subject="Re: Test",
                body="Reply body",
                reply_to_message_id=(
                    "graph-original"
                ),
                reply_mode="reply",
                attachments=[
                    {
                        "filename":
                            "proof.txt",

                        "content_type":
                            "text/plain",

                        "size":
                            5,

                        "content":
                            b"proof",
                    }
                ],
            )
        )


        calls = (
            mocked_post
            .call_args_list
        )


        self.assertEqual(
            len(
                calls
            ),
            3,
        )


        self.assertTrue(
            calls[0]
            .args[0]
            .endswith(
                "/messages/"
                "graph-original/"
                "createReply"
            )
        )


        self.assertEqual(
            calls[0]
            .kwargs[
                "json"
            ],
            {
                "comment":
                    "Reply body"
            },
        )


        self.assertTrue(
            calls[1]
            .args[0]
            .endswith(
                "/messages/"
                "reply-draft-1/"
                "attachments"
            )
        )


        self.assertEqual(
            calls[1]
            .kwargs[
                "json"
            ][
                "name"
            ],
            "proof.txt",
        )


        self.assertEqual(
            calls[1]
            .kwargs[
                "json"
            ][
                "contentBytes"
            ],
            (
                base64
                .b64encode(
                    b"proof"
                )
                .decode(
                    "ascii"
                )
            ),
        )


        self.assertTrue(
            calls[2]
            .args[0]
            .endswith(
                "/messages/"
                "reply-draft-1/"
                "send"
            )
        )


        self.assertEqual(
            result,
            {},
        )


        mocked_delete.assert_not_called()


    @patch(
        "email_accounts.services.microsoft_api."
        "requests.delete"
    )
    @patch(
        "email_accounts.services.microsoft_api."
        "requests.post"
    )
    @patch(
        "email_accounts.services.microsoft_api."
        "get_valid_oauth_token"
    )
    def test_outlook_reply_all_attachment_uses_create_reply_all(
        self,
        mocked_token,
        mocked_post,
        mocked_delete,
    ):
        token = MagicMock()

        token.access_token = (
            "microsoft-token"
        )

        mocked_token.return_value = (
            token
        )


        created = MagicMock()

        created.status_code = 201

        created.json.return_value = {
            "id":
                "reply-all-draft"
        }


        attached = MagicMock()

        attached.status_code = 201


        sent = MagicMock()

        sent.status_code = 202


        mocked_post.side_effect = [
            created,
            attached,
            sent,
        ]


        send_outlook_reply(
            user=object(),
            to_email=(
                "customer@example.com"
            ),
            subject="Re: Test",
            body="Reply all body",
            reply_to_message_id=(
                "graph-original"
            ),
            reply_mode="reply_all",
            attachments=[
                {
                    "filename":
                        "all.txt",

                    "content_type":
                        "text/plain",

                    "size":
                        3,

                    "content":
                        b"all",
                }
            ],
        )


        first_url = (
            mocked_post
            .call_args_list[0]
            .args[0]
        )


        self.assertTrue(
            first_url.endswith(
                "/messages/"
                "graph-original/"
                "createReplyAll"
            )
        )


        mocked_delete.assert_not_called()



# ============================================================
# R1C REAL MICROSOFT SENT RECONCILIATION REGRESSION
# ============================================================

from microsoftapis.services.outlook_sync import (
    _find_local_outbound_candidate,
)


class OutlookReplyThreadReconciliationTests(
    TestCase
):

    def setUp(
        self,
    ):

        User = get_user_model()


        self.user = (
            User.objects.create_user(
                email=(
                    "outlook-reconcile"
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
                    "Outlook Reconcile Org"
                ),
                slug=(
                    "outlook-reconcile-org"
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
                    "outlook-reconcile"
                    "@oneuch.local"
                ),
                account_type="outlook",
                credential_status="active",
                is_active=True,
            )
        )


    def create_placeholder(
        self,
        *,
        thread_id,
        body,
    ):

        conversation = (
            Conversation.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                email_account=(
                    self.account
                ),
                subject=(
                    "Re: Customer request"
                ),
                conversation_key=(
                    "outlook-placeholder-"
                    +
                    thread_id
                ),
                external_conversation_id=(
                    thread_id
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
                    self.account
                ),
                conversation=(
                    conversation
                ),
                platform="outlook",
                direction="outbound",
                folder="sent",
                external_message_id="sent",
                external_conversation_id=(
                    thread_id
                ),
                sender=(
                    self.account.email_address
                ),
                recipients=(
                    "customer@example.com"
                ),
                recipient_meta={
                    "to": [
                        {
                            "name":
                                "",

                            "email":
                                "customer@example.com",
                        }
                    ],

                    "cc":
                        [],

                    "bcc":
                        [],

                    "reply_to":
                        [],
                },
                subject=(
                    "Re: Customer request"
                ),
                body=body,
                received_at=(
                    timezone.now()
                ),
                status="sent",
                is_read=True,
            )
        )


    def test_thread_identity_survives_subject_case_and_body_formatting(
        self,
    ):

        candidate = (
            self.create_placeholder(
                thread_id=(
                    "graph-thread-one"
                ),
                body=(
                    "Reply body\n\n"
                    "One UCH signature"
                ),
            )
        )


        result = (
            _find_local_outbound_candidate(
                user=self.user,
                email_account=(
                    self.account
                ),
                subject=(
                    "RE: Customer request"
                ),
                recipients=[
                    "customer@example.com"
                ],
                body_preview=(
                    "Reply body "
                    "One UCH signature "
                    "From: Customer"
                ),
                sent_at=(
                    timezone.now()
                ),
                thread_id=(
                    "graph-thread-one"
                ),
            )
        )


        self.assertEqual(
            result,
            candidate,
        )


    def test_graph_thread_prevents_wrong_same_subject_candidate(
        self,
    ):

        wrong = (
            self.create_placeholder(
                thread_id=(
                    "graph-thread-wrong"
                ),
                body=(
                    "Same reply body"
                ),
            )
        )


        correct = (
            self.create_placeholder(
                thread_id=(
                    "graph-thread-correct"
                ),
                body=(
                    "Same reply body"
                ),
            )
        )


        result = (
            _find_local_outbound_candidate(
                user=self.user,
                email_account=(
                    self.account
                ),
                subject=(
                    "RE: Customer request"
                ),
                recipients=[
                    "customer@example.com"
                ],
                body_preview=(
                    "Same reply body"
                ),
                sent_at=(
                    timezone.now()
                ),
                thread_id=(
                    "graph-thread-correct"
                ),
            )
        )


        self.assertNotEqual(
            result,
            wrong,
        )


        self.assertEqual(
            result,
            correct,
        )
