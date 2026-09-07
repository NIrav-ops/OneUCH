import shutil
import tempfile

from email.message import (
    EmailMessage,
)

from types import (
    SimpleNamespace,
)

from unittest.mock import (
    patch,
)

from uuid import (
    uuid4,
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

from rest_framework.test import (
    APITestCase,
)

from email_accounts.models import (
    EmailAccount,
)

from email_accounts.services.imap_smtp import (
    _extract_imap_attachments,
    load_imap_attachment_content,
    send_via_smtp,
)

from inbox.models import (
    Conversation,
    InboxMessage,
    Organization,
    OrganizationUser,
)

from inbox.services.outbound_attachments import (
    IMAP_SMTP_RAW_LIMIT_BYTES,
    effective_attachment_limit_bytes,
)

from inbox.tasks import (
    send_email_task,
)


User = get_user_model()


class FakeSMTP:

    def __init__(
        self,
    ):
        self.login_args = None

        self.message = None

        self.from_addr = None

        self.to_addrs = None

        self.quit_called = False


    def login(
        self,
        username,
        password,
    ):
        self.login_args = (
            username,
            password,
        )

        return (
            235,
            b"authenticated",
        )


    def send_message(
        self,
        message,
        *,
        from_addr=None,
        to_addrs=None,
    ):
        self.message = (
            message
        )

        self.from_addr = (
            from_addr
        )

        self.to_addrs = list(
            to_addrs
            or []
        )

        return {}


    def quit(
        self,
    ):
        self.quit_called = True

        return (
            221,
            b"bye",
        )


    def close(
        self,
    ):
        return None


class FakeAttachmentIMAP:

    def __init__(
        self,
        *,
        raw,
        uidvalidity="777",
    ):
        self.raw = (
            raw
        )

        self.uidvalidity = (
            uidvalidity
        )

        self.logged_out = False


    def login(
        self,
        username,
        password,
    ):
        return (
            "OK",
            [
                b"authenticated"
            ],
        )


    def select(
        self,
        mailbox,
    ):
        return (
            "OK",
            [
                b"1"
            ],
        )


    def response(
        self,
        name,
    ):
        if name == "UIDVALIDITY":

            return (
                "UIDVALIDITY",
                [
                    str(
                        self.uidvalidity
                    ).encode(
                        "ascii"
                    )
                ],
            )

        return (
            name,
            [],
        )


    def uid(
        self,
        command,
        *args,
    ):
        if (
            str(
                command
            ).lower()
            !=
            "fetch"
        ):

            raise AssertionError(
                "unexpected IMAP UID command"
            )


        return (
            "OK",
            [
                (
                    b"1 (BODY[] {100})",
                    self.raw,
                )
            ],
        )


    def logout(
        self,
    ):
        self.logged_out = True

        return (
            "BYE",
            [
                b"logout"
            ],
        )


class MailRC1C5COutboundParityTests(
    APITestCase
):

    PASSWORD = (
        "C5C-User-Password-95371"
    )

    MAIL_CREDENTIAL = (
        "C5C-Synthetic-Mail-Credential-31479"
    )


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


        self.user = (
            User.objects.create_user(
                email=(
                    "c5c-owner@oneuch.test"
                ),
                password=(
                    self.PASSWORD
                ),
            )
        )


        self.organization = (
            Organization.objects.create(
                name="C5C Workspace",
                slug=(
                    "mail-c5c-"
                    + uuid4().hex
                ),
            )
        )


        OrganizationUser.objects.create(
            user=self.user,
            organization=(
                self.organization
            ),
            role="owner",
        )


        self.account = (
            EmailAccount.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                account_type="imap",
                email_address=(
                    "owner@example.com"
                ),
                imap_server=(
                    "imap.example.com"
                ),
                imap_port=993,
                smtp_server=(
                    "smtp.example.com"
                ),
                smtp_port=465,
                smtp_password=(
                    self.MAIL_CREDENTIAL
                ),
                credential_status="active",
                signature_enabled=True,
                signature_text=(
                    "-- C5C Signature"
                ),
                is_active=True,
            )
        )


        self.client.force_authenticate(
            user=self.user
        )


    @staticmethod
    def endpoint(
        host="smtp.example.com",
        port=465,
    ):
        return (
            SimpleNamespace(
                host=host,
                port=port,
            )
        )


    def source_conversation(
        self,
        *,
        key=None,
    ):
        return (
            Conversation.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                email_account=(
                    self.account
                ),
                subject="C5C source",
                conversation_key=(
                    key
                    or
                    (
                        "c5c-source-"
                        + uuid4().hex
                    )
                ),
                external_conversation_id=(
                    "<root@example.net>"
                ),
            )
        )


    def source_message(
        self,
        *,
        attachment_meta=None,
    ):
        conversation = (
            self.source_conversation()
        )


        message = (
            InboxMessage.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                email_account=(
                    self.account
                ),
                platform="imap",
                direction="inbound",
                folder="inbox",
                conversation=(
                    conversation
                ),
                external_message_id=(
                    "imap-rfc822-source"
                ),
                external_conversation_id=(
                    "<root@example.net>"
                ),
                sender=(
                    "customer@example.net"
                ),
                sender_meta={
                    "name":
                        "Customer",

                    "email":
                        "customer@example.net",
                },
                recipients=(
                    "owner@example.com, "
                    "finance@example.net"
                ),
                recipient_meta={
                    "to": [
                        {
                            "name":
                                "Owner",

                            "email":
                                "owner@example.com",
                        }
                    ],

                    "cc": [
                        {
                            "name":
                                "Finance",

                            "email":
                                "finance@example.net",
                        }
                    ],

                    "bcc":
                        [],

                    "reply_to":
                        [],
                },
                subject="C5C source",
                body="Original C5C message",
                attachment_meta=(
                    attachment_meta
                    or []
                ),
                received_at=(
                    timezone.now()
                ),
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


        return message


    # ========================================================
    # 1. IMAP participates in the governed outbound attachment
    # policy instead of being rejected as unsupported.
    # ========================================================

    def test_imap_attachment_policy_is_supported(
        self,
    ):
        self.assertEqual(
            effective_attachment_limit_bytes(
                account=(
                    self.account
                ),
                user=self.user,
            ),
            IMAP_SMTP_RAW_LIMIT_BYTES,
        )


    # ========================================================
    # 2. SMTP has true To/Cc/Bcc envelope roles and Bcc never
    # appears in serialized headers.
    # ========================================================

    def test_smtp_true_to_cc_bcc_envelope_and_bcc_privacy(
        self,
    ):
        fake = (
            FakeSMTP()
        )


        with (
            patch(
                (
                    "email_accounts.services."
                    "imap_smtp."
                    "validate_mailbox_endpoint"
                ),
                return_value=(
                    self.endpoint()
                ),
            ),
            patch(
                (
                    "email_accounts.services."
                    "imap_smtp."
                    "_PinnedSMTPSSL"
                ),
                return_value=(
                    fake
                ),
            ),
        ):

            result = (
                send_via_smtp(
                    email_account=(
                        self.account
                    ),
                    to_emails=[
                        {
                            "name":
                                "Alice",

                            "email":
                                "alice@example.net",
                        }
                    ],
                    cc_emails=[
                        {
                            "name":
                                "Bob",

                            "email":
                                "bob@example.net",
                        }
                    ],
                    bcc_emails=[
                        {
                            "name":
                                "Hidden",

                            "email":
                                "hidden@example.net",
                        }
                    ],
                    subject="C5C SMTP",
                    body="Hello",
                    password=(
                        self.MAIL_CREDENTIAL
                    ),
                )
            )


        self.assertIn(
            "alice@example.net",
            fake.message[
                "To"
            ],
        )

        self.assertIn(
            "bob@example.net",
            fake.message[
                "Cc"
            ],
        )

        self.assertIsNone(
            fake.message[
                "Bcc"
            ]
        )

        self.assertEqual(
            set(
                fake.to_addrs
            ),
            {
                "alice@example.net",
                "bob@example.net",
                "hidden@example.net",
            },
        )

        self.assertTrue(
            result[
                "id"
            ].startswith(
                "imap-rfc822-"
            )
        )

        self.assertTrue(
            result[
                "rfc_message_id"
            ].startswith(
                "<"
            )
        )


    # ========================================================
    # 3. SMTP attachment bytes + RFC thread headers are carried
    # by the provider message.
    # ========================================================

    def test_smtp_attachment_and_rfc_thread_headers(
        self,
    ):
        fake = (
            FakeSMTP()
        )


        with (
            patch(
                (
                    "email_accounts.services."
                    "imap_smtp."
                    "validate_mailbox_endpoint"
                ),
                return_value=(
                    self.endpoint()
                ),
            ),
            patch(
                (
                    "email_accounts.services."
                    "imap_smtp."
                    "_PinnedSMTPSSL"
                ),
                return_value=(
                    fake
                ),
            ),
        ):

            send_via_smtp(
                email_account=(
                    self.account
                ),
                to_email=(
                    "customer@example.net"
                ),
                subject="Re: C5C",
                body="Attached",
                in_reply_to=(
                    "<root@example.net>"
                ),
                references=(
                    "<root@example.net>"
                ),
                attachments=[
                    {
                        "filename":
                            "proof.txt",

                        "content_type":
                            "text/plain",

                        "size":
                            len(
                                b"proof"
                            ),

                        "content":
                            b"proof",
                    }
                ],
                password=(
                    self.MAIL_CREDENTIAL
                ),
            )


        self.assertEqual(
            fake.message[
                "In-Reply-To"
            ],
            "<root@example.net>",
        )

        self.assertEqual(
            fake.message[
                "References"
            ],
            "<root@example.net>",
        )


        attachments = [
            item
            for item in (
                fake.message.walk()
            )
            if (
                item.get_filename()
                ==
                "proof.txt"
            )
        ]


        self.assertEqual(
            len(
                attachments
            ),
            1,
        )

        self.assertEqual(
            attachments[0]
            .get_payload(
                decode=True
            ),
            b"proof",
        )


    # ========================================================
    # 4. Unified Compose now treats IMAP exactly like a governed
    # sending mailbox and materializes stable local Sent state.
    # ========================================================

    def test_unified_imap_compose_materializes_signed_sent_message(
        self,
    ):
        with (
            patch(
                (
                    "inbox.views.send_message."
                    "send_via_smtp"
                )
            ) as smtp_send,
            patch(
                (
                    "inbox.views.send_message."
                    "get_channel_layer"
                )
            ),
            patch(
                (
                    "inbox.views.send_message."
                    "async_to_sync"
                )
            ) as async_bridge,
        ):

            smtp_send.return_value = {
                "id":
                    "imap-rfc822-compose",

                "rfc_message_id":
                    "<compose@example.com>",
            }

            async_bridge.return_value = (
                lambda *args, **kwargs:
                    None
            )


            response = (
                self.client.post(
                    "/api/inbox/send/",
                    {
                        "account_id":
                            self.account.id,

                        "to": [
                            {
                                "name":
                                    "Customer",

                                "email":
                                    "customer@example.net",
                            }
                        ],

                        "cc": [
                            {
                                "name":
                                    "Finance",

                                "email":
                                    "finance@example.net",
                            }
                        ],

                        "bcc": [
                            {
                                "name":
                                    "Audit",

                                "email":
                                    "audit@example.net",
                            }
                        ],

                        "subject":
                            "C5C Compose",

                        "body":
                            "Compose body",
                    },
                    format="json",
                )
            )


        self.assertEqual(
            response.status_code,
            200,
        )


        kwargs = (
            smtp_send
            .call_args
            .kwargs
        )


        self.assertEqual(
            kwargs[
                "password"
            ],
            self.MAIL_CREDENTIAL,
        )

        self.assertIn(
            "-- C5C Signature",
            kwargs[
                "body"
            ],
        )

        self.assertEqual(
            kwargs[
                "cc_emails"
            ][0][
                "email"
            ],
            "finance@example.net",
        )

        self.assertEqual(
            kwargs[
                "bcc_emails"
            ][0][
                "email"
            ],
            "audit@example.net",
        )


        sent = (
            InboxMessage.objects
            .get(
                id=response.data[
                    "message_id"
                ]
            )
        )


        self.assertEqual(
            sent.platform,
            "imap",
        )

        self.assertEqual(
            sent.folder,
            "sent",
        )

        self.assertEqual(
            sent.external_message_id,
            "imap-rfc822-compose",
        )

        self.assertEqual(
            sent.external_conversation_id,
            "<compose@example.com>",
        )

        self.assertEqual(
            sent.recipient_meta[
                "bcc"
            ][0][
                "email"
            ],
            "audit@example.net",
        )


    # ========================================================
    # 5. A non-valid IMAP credential is blocked before SMTP.
    # ========================================================

    def test_unified_imap_compose_blocks_invalid_credential_before_smtp(
        self,
    ):
        self.account.credential_status = (
            "reauth_required"
        )

        self.account.save(
            update_fields=[
                "credential_status",
            ]
        )


        with patch(
            (
                "inbox.views.send_message."
                "send_via_smtp"
            )
        ) as smtp_send:

            response = (
                self.client.post(
                    "/api/inbox/send/",
                    {
                        "account_id":
                            self.account.id,

                        "to":
                            "customer@example.net",

                        "subject":
                            "Blocked",

                        "body":
                            "Do not send",
                    },
                    format="json",
                )
            )


        self.assertEqual(
            response.status_code,
            400,
        )

        smtp_send.assert_not_called()


    # ========================================================
    # 6. Compose-uploaded files reach SMTP through the same
    # governed attachment structure as Gmail/Microsoft.
    # ========================================================

    def test_unified_imap_compose_supports_uploaded_attachment(
        self,
    ):
        with (
            patch(
                (
                    "inbox.views.send_message."
                    "send_via_smtp"
                )
            ) as smtp_send,
            patch(
                (
                    "inbox.views.send_message."
                    "get_channel_layer"
                )
            ),
            patch(
                (
                    "inbox.views.send_message."
                    "async_to_sync"
                )
            ) as async_bridge,
        ):

            smtp_send.return_value = {
                "id":
                    "imap-rfc822-file",

                "rfc_message_id":
                    "<file@example.com>",
            }

            async_bridge.return_value = (
                lambda *args, **kwargs:
                    None
            )


            response = (
                self.client.post(
                    "/api/inbox/send/",
                    {
                        "account_id":
                            self.account.id,

                        "to":
                            "customer@example.net",

                        "subject":
                            "C5C attachment",

                        "body":
                            "Please see attached.",

                        "attachments":
                            SimpleUploadedFile(
                                "compose.txt",
                                b"compose-file",
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


        attachments = (
            smtp_send
            .call_args
            .kwargs[
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
            attachments[0][
                "filename"
            ],
            "compose.txt",
        )

        self.assertEqual(
            attachments[0][
                "content"
            ],
            b"compose-file",
        )


    # ========================================================
    # 7. Reply All now sends true To/Cc, persisted attachments,
    # the managed signature, and RFC thread context through SMTP.
    # ========================================================

    def test_imap_reply_all_delivers_cc_attachment_and_thread_context(
        self,
    ):
        source = (
            self.source_message()
        )


        with patch(
            (
                "inbox.views.reply."
                "send_email_task.delay"
            )
        ):

            response = (
                self.client.post(
                    (
                        "/api/inbox/conversations/"
                        + str(
                            source.conversation_id
                        )
                        + "/reply/"
                    ),
                    {
                        "body":
                            "Reply body",

                        "mode":
                            "reply_all",

                        "attachments":
                            SimpleUploadedFile(
                                "reply.txt",
                                b"reply-proof",
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


        reply = (
            InboxMessage.objects
            .get(
                id=response.data[
                    "message_id"
                ]
            )
        )


        self.assertIn(
            "-- C5C Signature",
            reply.body,
        )


        with (
            patch(
                (
                    "inbox.tasks."
                    "get_outbound_intent_for_message"
                ),
                return_value=None,
            ),
            patch(
                (
                    "inbox.tasks."
                    "send_via_smtp"
                )
            ) as smtp_send,
        ):

            smtp_send.return_value = {
                "id":
                    "imap-rfc822-reply",

                "rfc_message_id":
                    "<reply@example.com>",
            }


            result = (
                send_email_task.run(
                    self.account.id,
                    "customer@example.net",
                    reply.subject,
                    reply.body,
                    reply.id,
                    "reply_all",
                )
            )


        kwargs = (
            smtp_send
            .call_args
            .kwargs
        )


        self.assertIn(
            "finance@example.net",
            kwargs[
                "to_email"
            ],
        )

        self.assertEqual(
            kwargs[
                "cc_emails"
            ][0][
                "email"
            ],
            "finance@example.net",
        )

        self.assertEqual(
            kwargs[
                "in_reply_to"
            ],
            "<root@example.net>",
        )

        self.assertEqual(
            kwargs[
                "references"
            ],
            "<root@example.net>",
        )

        self.assertEqual(
            kwargs[
                "attachments"
            ][0][
                "content"
            ],
            b"reply-proof",
        )


        reply.refresh_from_db()


        self.assertEqual(
            result[
                "status"
            ],
            "sent",
        )

        self.assertEqual(
            reply.status,
            "sent",
        )

        self.assertEqual(
            reply.folder,
            "sent",
        )

        self.assertEqual(
            reply.external_message_id,
            "imap-rfc822-reply",
        )


    # ========================================================
    # 8. Draft Send delegates to the unified IMAP path and
    # removes the local draft only after successful delivery.
    # ========================================================

    def test_imap_draft_send_uses_unified_delivery(
        self,
    ):
        conversation = (
            self.source_conversation(
                key=(
                    "c5c-draft-"
                    + uuid4().hex
                )
            )
        )


        draft = (
            InboxMessage.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                email_account=(
                    self.account
                ),
                platform="imap",
                direction="outbound",
                folder="draft",
                conversation=(
                    conversation
                ),
                external_message_id=(
                    "draft-"
                    + str(
                        conversation.id
                    )
                ),
                sender=(
                    self.account.email_address
                ),
                recipients=(
                    "customer@example.net"
                ),
                recipient_meta={
                    "to": [
                        {
                            "name":
                                "Customer",

                            "email":
                                "customer@example.net",
                        }
                    ],

                    "cc":
                        [],

                    "bcc":
                        [],

                    "reply_to":
                        [],
                },
                subject="C5C draft",
                body="Draft body",
                received_at=(
                    timezone.now()
                ),
                is_draft=True,
                status="queued",
            )
        )


        with (
            patch(
                (
                    "inbox.views.send_message."
                    "resolve_outbound_idempotency_key"
                ),
                return_value=None,
            ),
            patch(
                (
                    "inbox.views.send_message."
                    "send_via_smtp"
                )
            ) as smtp_send,
            patch(
                (
                    "inbox.views.send_message."
                    "get_channel_layer"
                )
            ),
            patch(
                (
                    "inbox.views.send_message."
                    "async_to_sync"
                )
            ) as async_bridge,
        ):

            smtp_send.return_value = {
                "id":
                    "imap-rfc822-draft",

                "rfc_message_id":
                    "<draft@example.com>",
            }

            async_bridge.return_value = (
                lambda *args, **kwargs:
                    None
            )


            response = (
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
            response.status_code,
            200,
        )

        self.assertFalse(
            InboxMessage.objects
            .filter(
                id=draft.id
            )
            .exists()
        )

        self.assertIn(
            "-- C5C Signature",
            smtp_send
            .call_args
            .kwargs[
                "body"
            ],
        )


    # ========================================================
    # 9. Forward combines selected original IMAP attachments
    # and newly uploaded files, then delegates to unified SMTP.
    # ========================================================

    def test_imap_forward_supports_original_and_user_attachments(
        self,
    ):
        source = (
            self.source_message(
                attachment_meta=[
                    {
                        "filename":
                            "original.txt",

                        "attachment_id":
                            (
                                "imap:inbox:"
                                "777:10:2"
                            ),

                        "mime_type":
                            "text/plain",

                        "size":
                            len(
                                b"original"
                            ),
                    }
                ]
            )
        )


        with (
            patch(
                (
                    "inbox.services."
                    "forward_attachments."
                    "load_imap_attachment_content"
                ),
                return_value=(
                    b"original"
                ),
            ) as loader,
            patch(
                (
                    "inbox.views.send_message."
                    "send_via_smtp"
                )
            ) as smtp_send,
            patch(
                (
                    "inbox.views.send_message."
                    "get_channel_layer"
                )
            ),
            patch(
                (
                    "inbox.views.send_message."
                    "async_to_sync"
                )
            ) as async_bridge,
        ):

            smtp_send.return_value = {
                "id":
                    "imap-rfc822-forward",

                "rfc_message_id":
                    "<forward@example.com>",
            }

            async_bridge.return_value = (
                lambda *args, **kwargs:
                    None
            )


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
                            "forward@example.net",

                        "body":
                            "Forwarding",

                        "attachments":
                            SimpleUploadedFile(
                                "added.txt",
                                b"added",
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


        loader.assert_called_once_with(
            email_account=(
                self.account
            ),
            attachment_id=(
                "imap:inbox:777:10:2"
            ),
        )


        attachments = (
            smtp_send
            .call_args
            .kwargs[
                "attachments"
            ]
        )


        self.assertEqual(
            {
                item[
                    "filename"
                ]
                for item in (
                    attachments
                )
            },
            {
                "original.txt",
                "added.txt",
            },
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
            smtp_send
            .call_args
            .kwargs[
                "body"
            ]
            .count(
                "-- C5C Signature"
            ),
            1,
        )


    # ========================================================
    # 10. C5B ingestion metadata now receives a retrievable,
    # UIDVALIDITY-bound attachment locator.
    # ========================================================

    def test_imap_attachment_metadata_contains_retrieval_locator(
        self,
    ):
        message = (
            EmailMessage()
        )

        message[
            "From"
        ] = (
            "customer@example.net"
        )

        message[
            "To"
        ] = (
            "owner@example.com"
        )

        message[
            "Subject"
        ] = (
            "Attachment locator"
        )

        message.set_content(
            "Body"
        )

        message.add_attachment(
            b"original-proof",
            maintype="application",
            subtype="octet-stream",
            filename="proof.bin",
        )


        attachments = (
            _extract_imap_attachments(
                message,
                folder_key="inbox",
                uidvalidity="777",
                uid="10",
            )
        )


        self.assertEqual(
            len(
                attachments
            ),
            1,
        )

        self.assertTrue(
            attachments[0][
                "attachment_id"
            ].startswith(
                "imap:inbox:777:10:"
            )
        )

        self.assertEqual(
            attachments[0][
                "size"
            ],
            len(
                b"original-proof"
            ),
        )


    # ========================================================
    # 11. The locator retrieves exactly the requested MIME part
    # through the pinned IMAP client.
    # ========================================================

    def test_imap_attachment_loader_fetches_exact_mime_part(
        self,
    ):
        message = (
            EmailMessage()
        )

        message[
            "From"
        ] = (
            "customer@example.net"
        )

        message[
            "To"
        ] = (
            "owner@example.com"
        )

        message[
            "Subject"
        ] = (
            "Loader"
        )

        message.set_content(
            "Body"
        )

        message.add_attachment(
            b"loader-proof",
            maintype="application",
            subtype="octet-stream",
            filename="loader.bin",
        )


        metadata = (
            _extract_imap_attachments(
                message,
                folder_key="inbox",
                uidvalidity="777",
                uid="10",
            )
        )


        locator = (
            metadata[0][
                "attachment_id"
            ]
        )


        fake = (
            FakeAttachmentIMAP(
                raw=(
                    message.as_bytes()
                ),
                uidvalidity="777",
            )
        )


        with (
            patch(
                (
                    "email_accounts.services."
                    "imap_smtp."
                    "validate_mailbox_endpoint"
                ),
                return_value=(
                    self.endpoint(
                        host=(
                            "imap.example.com"
                        ),
                        port=993,
                    )
                ),
            ),
            patch(
                (
                    "email_accounts.services."
                    "imap_smtp."
                    "_PinnedIMAP4SSL"
                ),
                return_value=(
                    fake
                ),
            ),
        ):

            content = (
                load_imap_attachment_content(
                    email_account=(
                        self.account
                    ),
                    attachment_id=(
                        locator
                    ),
                )
            )


        self.assertEqual(
            content,
            b"loader-proof",
        )

        self.assertTrue(
            fake.logged_out
        )


    # ========================================================
    # 12. UIDVALIDITY mismatch fails closed rather than reading
    # the same numeric UID from a replacement mailbox epoch.
    # ========================================================

    def test_imap_attachment_loader_blocks_uidvalidity_mismatch(
        self,
    ):
        message = (
            EmailMessage()
        )

        message[
            "From"
        ] = (
            "customer@example.net"
        )

        message[
            "To"
        ] = (
            "owner@example.com"
        )

        message.set_content(
            "Body"
        )

        message.add_attachment(
            b"mismatch-proof",
            maintype="application",
            subtype="octet-stream",
            filename="mismatch.bin",
        )


        locator = (
            _extract_imap_attachments(
                message,
                folder_key="inbox",
                uidvalidity="777",
                uid="10",
            )[0][
                "attachment_id"
            ]
        )


        fake = (
            FakeAttachmentIMAP(
                raw=(
                    message.as_bytes()
                ),
                uidvalidity="999",
            )
        )


        with (
            patch(
                (
                    "email_accounts.services."
                    "imap_smtp."
                    "validate_mailbox_endpoint"
                ),
                return_value=(
                    self.endpoint(
                        host=(
                            "imap.example.com"
                        ),
                        port=993,
                    )
                ),
            ),
            patch(
                (
                    "email_accounts.services."
                    "imap_smtp."
                    "_PinnedIMAP4SSL"
                ),
                return_value=(
                    fake
                ),
            ),
        ):

            with self.assertRaisesRegex(
                RuntimeError,
                "UIDVALIDITY changed",
            ):

                load_imap_attachment_content(
                    email_account=(
                        self.account
                    ),
                    attachment_id=(
                        locator
                    ),
                )

    # ========================================================
    # 13. A retrievable attachment locator must never be
    # created without UIDVALIDITY. Numeric UIDs are not safe
    # across mailbox epochs by themselves.
    # ========================================================

    def test_imap_attachment_metadata_requires_uidvalidity(
        self,
    ):
        message = (
            EmailMessage()
        )

        message[
            "From"
        ] = (
            "customer@example.net"
        )

        message[
            "To"
        ] = (
            "owner@example.com"
        )

        message[
            "Subject"
        ] = (
            "UIDVALIDITY required"
        )

        message.set_content(
            "Body"
        )

        message.add_attachment(
            b"uidvalidity-proof",
            maintype="application",
            subtype="octet-stream",
            filename="proof.bin",
        )


        with self.assertRaisesRegex(
            ValueError,
            "requires UIDVALIDITY",
        ):

            _extract_imap_attachments(
                message,
                folder_key="inbox",
                uidvalidity=None,
                uid="10",
            )
