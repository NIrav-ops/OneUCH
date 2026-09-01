from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.utils import timezone

from rest_framework.test import APITestCase

from email_accounts.models import EmailAccount
from inbox.models import (
    Conversation,
    InboxMessage,
    Organization,
    OrganizationUser,
)


class ConversationBulkAPITests(APITestCase):

    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            email="bulk-user@oneuch.local",
            password="test-password-123",
        )

        self.organization = Organization.objects.create(
            name="Bulk Test Organization",
            slug="bulk-test-organization",
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=self.organization,
            role="member",
        )

        self.email_account = EmailAccount.objects.create(
            user=self.user,
            email_address="bulk-user@oneuch.local",
            account_type="gmail",
            credential_status="active",
            is_active=True,
        )

        self.conversation = Conversation.objects.create(
            user=self.user,
            organization=self.organization,
            email_account=self.email_account,
            subject="Bulk Test",
            conversation_key="bulk-test-key",
            external_conversation_id="gmail-thread-001",
            unread_count=1,
        )

        self.message = InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            email_account=self.email_account,
            conversation=self.conversation,
            platform="gmail",
            direction="inbound",
            external_message_id="gmail-message-001",
            external_conversation_id="gmail-thread-001",
            sender="customer@example.com",
            recipients="bulk-user@oneuch.local",
            subject="Bulk Test",
            body="Unread message",
            received_at=timezone.now(),
            is_read=False,
            status="sent",
        )

    def test_bulk_read_requires_authentication(self):
        response = self.client.post(
            "/api/inbox/conversation/bulk-mark-read/",
            {
                "conversation_ids": [
                    self.conversation.id
                ]
            },
            format="json",
        )

        self.assertIn(
            response.status_code,
            {401, 403},
        )

    @patch(
        "inbox.services.mail_mutations.build"
    )
    @patch(
        "inbox.services.mail_mutations."
        "get_gmail_credentials"
    )
    def test_bulk_read_accepts_numeric_conversation_id(
        self,
        mocked_credentials,
        mocked_build,
    ):
        service = MagicMock()

        mocked_build.return_value = service

        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.post(
            "/api/inbox/conversation/bulk-mark-read/",
            {
                "conversation_ids": [
                    self.conversation.id
                ]
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.conversation.refresh_from_db()
        self.message.refresh_from_db()

        self.assertEqual(
            self.conversation.unread_count,
            0,
        )

        self.assertTrue(
            self.message.is_read
        )

        self.assertEqual(
            response.data["updated"][0][
                "conversation_id"
            ],
            self.conversation.id,
        )

    @patch(
        "inbox.services.mail_mutations.build"
    )
    @patch(
        "inbox.services.mail_mutations."
        "get_gmail_credentials"
    )
    def test_bulk_star_accepts_numeric_conversation_id(
        self,
        mocked_credentials,
        mocked_build,
    ):
        service = MagicMock()

        mocked_build.return_value = service

        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.post(
            "/api/inbox/conversation/bulk-toggle-star/",
            {
                "conversation_ids": [
                    self.conversation.id
                ]
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.conversation.refresh_from_db()
        self.message.refresh_from_db()

        self.assertTrue(
            self.conversation.is_starred
        )

        self.assertTrue(
            self.message.is_starred
        )

        self.assertEqual(
            response.data["updated"][0][
                "conversation_id"
            ],
            self.conversation.id,
        )
