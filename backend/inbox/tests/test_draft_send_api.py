from unittest.mock import patch

from django.contrib.auth import get_user_model
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


class DraftSendAPITests(APITestCase):

    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            email="draft-user@oneuch.local",
            password="test-password-123",
        )

        self.organization = Organization.objects.create(
            name="Draft Test Organization",
            slug="draft-test-organization",
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=self.organization,
            role="member",
        )

        self.email_account = EmailAccount.objects.create(
            user=self.user,
            email_address="draft-user@oneuch.local",
            account_type="gmail",
            credential_status="active",
            is_active=True,
        )

        self.conversation = Conversation.objects.create(
            user=self.user,
            organization=self.organization,
            email_account=self.email_account,
            subject="Draft subject",
            conversation_key="draft-send-test-conversation",
        )

        self.draft = InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            email_account=self.email_account,
            folder="draft",
            platform="gmail",
            direction="outbound",
            conversation=self.conversation,
            external_message_id="draft-test-message",
            sender="draft-user@oneuch.local",
            recipients="customer@example.com",
            subject="Draft subject",
            body="Draft body",
            received_at=timezone.now(),
            is_read=True,
            is_draft=True,
            status="queued",
        )

        self.url = (
            f"/api/inbox/draft/send/"
            f"{self.draft.id}/"
        )

    def test_send_draft_requires_authentication(self):
        response = self.client.post(
            self.url,
            {},
            format="json",
        )

        self.assertIn(
            response.status_code,
            {401, 403},
        )

    def test_user_cannot_send_another_users_draft(self):
        User = get_user_model()

        other_user = User.objects.create_user(
            email="other-draft-user@oneuch.local",
            password="test-password-123",
        )

        self.client.force_authenticate(
            user=other_user
        )

        response = self.client.post(
            self.url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertTrue(
            InboxMessage.objects.filter(
                id=self.draft.id
            ).exists()
        )

    @patch(
        "inbox.views.send_message."
        "UnifiedSendMessageAPIView.send_with_data"
    )
    def test_successful_send_deletes_draft(
        self,
        mocked_send,
    ):
        mocked_send.return_value = Response(
            {
                "status": "sent",
                "conversation_id": self.conversation.id,
                "message_id": 999,
            },
            status=200,
        )

        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.post(
            self.url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["status"],
            "draft_sent",
        )

        self.assertFalse(
            InboxMessage.objects.filter(
                id=self.draft.id
            ).exists()
        )

        mocked_send.assert_called_once()

        payload = (
            mocked_send.call_args.kwargs[
                "data"
            ]
        )

        self.assertEqual(
            payload["to"],
            "customer@example.com",
        )

        self.assertEqual(
            payload["subject"],
            "Draft subject",
        )

        self.assertEqual(
            payload["body"],
            "Draft body",
        )

        self.assertEqual(
            payload["conversation_id"],
            self.conversation.id,
        )

        self.assertEqual(
            payload["account_id"],
            self.email_account.id,
        )

    @patch(
        "inbox.views.send_message."
        "UnifiedSendMessageAPIView.send_with_data"
    )
    def test_failed_send_keeps_draft(
        self,
        mocked_send,
    ):
        mocked_send.return_value = Response(
            {
                "error": "Provider unavailable",
            },
            status=500,
        )

        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.post(
            self.url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            500,
        )

        self.assertTrue(
            InboxMessage.objects.filter(
                id=self.draft.id
            ).exists()
        )