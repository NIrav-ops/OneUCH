import json
import os
import shutil
import tempfile

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone

from rest_framework.response import Response
from rest_framework.test import APITestCase

from email_accounts.models import EmailAccount

from inbox.models import (
    Conversation,
    InboxMessage,
    Organization,
    OrganizationUser,
)

from inbox.services.persistent_outbound_attachments import (
    persist_outbound_attachments,
)


class DraftAttachmentPersistenceTests(
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
                    "draft-attachments"
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
                    "Draft Attachment Organization"
                ),
                slug=(
                    "draft-attachment-organization"
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
                    "draft-gmail"
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
                    "draft-outlook"
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


        self.save_url = (
            "/api/inbox/draft/save/"
        )


    def save_draft(
        self,
        *,
        account,
        filename,
        content,
        draft_id=None,
        conversation_id=None,
        retained=None,
    ):

        payload = {
            "subject":
                "Persistent draft attachment",

            "body":
                "Draft body",

            "to":
                "customer@example.com",

            "cc":
                "",

            "bcc":
                "",

            "account_id":
                str(
                    account.id
                ),

            "retained_attachment_ids":
                json.dumps(
                    retained
                    or []
                ),

            "attachments":
                SimpleUploadedFile(
                    filename,
                    content,
                    content_type=(
                        "text/plain"
                    ),
                ),
        }


        if draft_id:

            payload[
                "draft_id"
            ] = str(
                draft_id
            )


        if conversation_id:

            payload[
                "conversation_id"
            ] = str(
                conversation_id
            )


        return (
            self.client.post(
                self.save_url,
                payload,
                format="multipart",
            )
        )


    def test_new_draft_attachment_is_persisted_and_listed(
        self,
    ):

        content = (
            b"persistent-draft-proof"
        )


        response = (
            self.save_draft(
                account=self.gmail,
                filename="proof.txt",
                content=content,
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
            content,
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


        listed = (
            list_response.data[0]
        )


        self.assertEqual(
            listed[
                "attachment_count"
            ],
            1,
        )


        self.assertEqual(
            listed[
                "attachments"
            ][0][
                "filename"
            ],
            "proof.txt",
        )


        self.assertTrue(
            listed[
                "attachments"
            ][0][
                "saved"
            ]
        )


    def test_edit_can_retain_add_and_remove_saved_files(
        self,
    ):

        first = (
            self.save_draft(
                account=self.gmail,
                filename="first.txt",
                content=b"first",
            )
        )


        self.assertEqual(
            first.status_code,
            200,
        )


        draft_id = (
            first.data[
                "draft_id"
            ]
        )


        conversation_id = (
            first.data[
                "conversation_id"
            ]
        )


        draft = (
            InboxMessage.objects
            .get(
                id=draft_id
            )
        )


        first_attachment = (
            draft.attachments.first()
        )


        first_storage_path = (
            first_attachment.file.path
        )


        second = (
            self.save_draft(
                account=self.gmail,
                filename="second.txt",
                content=b"second",
                draft_id=draft_id,
                conversation_id=(
                    conversation_id
                ),
                retained=[
                    first_attachment.id
                ],
            )
        )


        self.assertEqual(
            second.status_code,
            200,
        )


        self.assertEqual(
            second.data[
                "attachment_count"
            ],
            2,
        )


        draft.refresh_from_db()


        attachments = list(
            draft.attachments
            .all()
            .order_by(
                "id"
            )
        )


        self.assertEqual(
            len(
                attachments
            ),
            2,
        )


        second_attachment = (
            attachments[1]
        )


        remove_response = (
            self.client.post(
                self.save_url,
                {
                    "draft_id":
                        str(
                            draft.id
                        ),

                    "conversation_id":
                        str(
                            conversation_id
                        ),

                    "subject":
                        "Persistent draft attachment",

                    "body":
                        "Draft body edited",

                    "to":
                        "customer@example.com",

                    "cc":
                        "",

                    "bcc":
                        "",

                    "account_id":
                        str(
                            self.gmail.id
                        ),

                    "retained_attachment_ids":
                        json.dumps(
                            [
                                second_attachment.id
                            ]
                        ),
                },
                format="multipart",
            )
        )


        self.assertEqual(
            remove_response.status_code,
            200,
        )


        self.assertEqual(
            remove_response.data[
                "attachment_count"
            ],
            1,
        )


        self.assertFalse(
            draft.attachments
            .filter(
                id=(
                    first_attachment.id
                )
            )
            .exists()
        )


        self.assertTrue(
            draft.attachments
            .filter(
                id=(
                    second_attachment.id
                )
            )
            .exists()
        )


        self.assertFalse(
            os.path.exists(
                first_storage_path
            )
        )


    def test_retained_file_plus_new_file_obeys_combined_policy(
        self,
    ):

        first = (
            self.save_draft(
                account=self.outlook,
                filename="first.txt",
                content=(
                    b"a"
                    *
                    (
                        2
                        *
                        1024
                        *
                        1024
                    )
                ),
            )
        )


        self.assertEqual(
            first.status_code,
            200,
        )


        draft = (
            InboxMessage.objects
            .get(
                id=first.data[
                    "draft_id"
                ]
            )
        )


        attachment = (
            draft.attachments.first()
        )


        second = (
            self.save_draft(
                account=self.outlook,
                filename="second.txt",
                content=(
                    b"b"
                    *
                    (
                        2
                        *
                        1024
                        *
                        1024
                    )
                ),
                draft_id=(
                    draft.id
                ),
                conversation_id=(
                    draft.conversation_id
                ),
                retained=[
                    attachment.id
                ],
            )
        )


        self.assertEqual(
            second.status_code,
            400,
        )


        self.assertIn(
            "3 MB",
            second.data[
                "error"
            ],
        )


        draft.refresh_from_db()


        self.assertEqual(
            draft.attachments.count(),
            1,
        )


class DraftAttachmentSendTests(
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
                    "draft-send-files"
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
                    "Draft Send File Organization"
                ),
                slug=(
                    "draft-send-file-organization"
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
                    "draft-send-files"
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
                subject="Draft with file",
                conversation_key=(
                    "draft-with-file"
                ),
            )
        )


        self.draft = (
            InboxMessage.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                email_account=(
                    self.account
                ),
                folder="draft",
                platform="gmail",
                direction="outbound",
                conversation=(
                    self.conversation
                ),
                external_message_id=(
                    "draft-file-message"
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
                subject="Draft with file",
                body="Draft body",
                received_at=(
                    timezone.now()
                ),
                is_read=True,
                is_draft=True,
                status="queued",
            )
        )


        persist_outbound_attachments(
            message=self.draft,
            prepared=[
                {
                    "filename":
                        "saved.txt",

                    "content_type":
                        "text/plain",

                    "size":
                        len(
                            b"saved-file-bytes"
                        ),

                    "content":
                        b"saved-file-bytes",
                }
            ],
        )


        self.client.force_authenticate(
            user=self.user
        )


        self.url = (
            "/api/inbox/draft/send/"
            +
            str(
                self.draft.id
            )
            +
            "/"
        )


    @patch(
        "inbox.views.send_message."
        "UnifiedSendMessageAPIView.send_with_data"
    )
    def test_send_draft_rehydrates_and_moves_saved_attachment(
        self,
        mocked_send,
    ):

        sent = (
            InboxMessage.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                email_account=(
                    self.account
                ),
                folder="sent",
                platform="gmail",
                direction="outbound",
                conversation=(
                    self.conversation
                ),
                external_message_id=(
                    "provider-sent-file"
                ),
                sender=(
                    self.account.email_address
                ),
                recipients=(
                    "customer@example.com"
                ),
                subject="Draft with file",
                body="Draft body",
                received_at=(
                    timezone.now()
                ),
                is_read=True,
                is_draft=False,
                status="sent",
            )
        )


        mocked_send.return_value = (
            Response(
                {
                    "status":
                        "sent",

                    "conversation_id":
                        self.conversation.id,

                    "message_id":
                        sent.id,
                },
                status=200,
            )
        )


        original_attachment = (
            self.draft.attachments.first()
        )


        response = (
            self.client.post(
                self.url,
                {},
                format="json",
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


        kwargs = (
            mocked_send
            .call_args
            .kwargs
        )


        self.assertIn(
            "prepared_attachments",
            kwargs,
        )


        prepared = (
            kwargs[
                "prepared_attachments"
            ]
        )


        self.assertEqual(
            prepared[0][
                "filename"
            ],
            "saved.txt",
        )


        self.assertEqual(
            prepared[0][
                "content"
            ],
            b"saved-file-bytes",
        )


        self.assertFalse(
            InboxMessage.objects
            .filter(
                id=(
                    self.draft.id
                )
            )
            .exists()
        )


        original_attachment.refresh_from_db()


        self.assertEqual(
            original_attachment.message_id,
            sent.id,
        )


        sent.refresh_from_db()


        self.assertEqual(
            sent.attachment_meta[0][
                "filename"
            ],
            "saved.txt",
        )


    @patch(
        "inbox.views.send_message."
        "UnifiedSendMessageAPIView.send_with_data"
    )
    def test_failed_send_keeps_draft_and_saved_attachment(
        self,
        mocked_send,
    ):

        mocked_send.return_value = (
            Response(
                {
                    "error":
                        "Provider unavailable"
                },
                status=500,
            )
        )


        attachment = (
            self.draft.attachments.first()
        )


        response = (
            self.client.post(
                self.url,
                {},
                format="json",
            )
        )


        self.assertEqual(
            response.status_code,
            500,
        )


        self.assertTrue(
            InboxMessage.objects
            .filter(
                id=(
                    self.draft.id
                )
            )
            .exists()
        )


        self.assertTrue(
            self.draft.attachments
            .filter(
                id=(
                    attachment.id
                )
            )
            .exists()
        )
