from unittest.mock import patch

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


class ReplyConversationAPITests(APITestCase):

    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            email="reply-user@oneuch.local",
            password="test-password-123",
        )

        self.organization = Organization.objects.create(
            name="Reply Test Organization",
            slug="reply-test-organization",
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=self.organization,
            role="member",
        )

        self.email_account = EmailAccount.objects.create(
            user=self.user,
            email_address="reply-user@oneuch.local",
            account_type="gmail",
            credential_status="active",
            is_active=True,
        )

        self.conversation = Conversation.objects.create(
            user=self.user,
            organization=self.organization,
            email_account=self.email_account,
            subject="Customer requirement",
            conversation_key="reply-test-conversation",
        )

        self.inbound_message = InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            email_account=self.email_account,
            folder="inbox",
            platform="gmail",
            direction="inbound",
            conversation=self.conversation,
            external_message_id="external-message-001",
            sender="customer@example.com",
            recipients="reply-user@oneuch.local",
            subject="Customer requirement",
            body="Please share an update.",
            received_at=timezone.now(),
            is_read=True,
            status="sent",
        )

        self.url = (
            f"/api/inbox/conversations/"
            f"{self.conversation.id}/reply/"
        )

    def test_reply_requires_authentication(self):
        response = self.client.post(
            self.url,
            {
                "body": "Test reply",
            },
            format="json",
        )

        self.assertIn(
            response.status_code,
            {401, 403},
        )

    def test_reply_rejects_empty_body(self):
        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.post(
            self.url,
            {
                "body": "",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertEqual(
            response.data["error"],
            "Reply body is required",
        )

    def test_user_cannot_reply_to_another_users_conversation(self):
        User = get_user_model()

        other_user = User.objects.create_user(
            email="other-user@oneuch.local",
            password="test-password-123",
        )

        other_organization = Organization.objects.create(
            name="Other Organization",
            slug="other-organization",
        )

        OrganizationUser.objects.create(
            user=other_user,
            organization=other_organization,
            role="member",
        )

        other_conversation = Conversation.objects.create(
            user=other_user,
            organization=other_organization,
            subject="Private conversation",
            conversation_key="other-users-conversation",
        )

        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.post(
            (
                f"/api/inbox/conversations/"
                f"{other_conversation.id}/reply/"
            ),
            {
                "body": "Unauthorized reply attempt",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertEqual(
            response.data["error"],
            "Conversation not found",
        )

    @patch(
        "inbox.views.reply.send_email_task.delay"
    )
    def test_valid_reply_creates_outbound_message_and_queues_send(
        self,
        mocked_send_delay,
    ):
        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.post(
            self.url,
            {
                "body": "Here is the requested update.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            202,
        )

        self.assertEqual(
            response.data["status"],
            "Reply queued successfully",
        )

        reply = InboxMessage.objects.get(
            conversation=self.conversation,
            direction="outbound",
        )

        self.assertEqual(
            reply.user,
            self.user,
        )

        self.assertEqual(
            reply.organization,
            self.organization,
        )

        self.assertEqual(
            reply.email_account,
            self.email_account,
        )

        self.assertEqual(
            reply.platform,
            "gmail",
        )

        self.assertEqual(
            reply.sender,
            "reply-user@oneuch.local",
        )

        self.assertEqual(
            reply.recipients,
            "customer@example.com",
        )

        self.assertEqual(
            reply.subject,
            "Re: Customer requirement",
        )

        self.assertEqual(
            reply.body,
            "Here is the requested update.",
        )

        self.assertEqual(
            reply.in_reply_to,
            "external-message-001",
        )

        self.assertEqual(
            reply.status,
            "queued",
        )

        mocked_send_delay.assert_called_once_with(
            self.email_account.id,
            "customer@example.com",
            "Re: Customer requirement",
            "Here is the requested update.",
            reply.id,
        )