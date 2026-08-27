from unittest.mock import patch

from celery.exceptions import Retry
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from email_accounts.models import EmailAccount
from inbox.models import (
    Conversation,
    InboxMessage,
    Organization,
    OrganizationUser,
)
from inbox.tasks import send_email_task


class ReplyDeliveryTaskTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            email="delivery-user@oneuch.local",
            password="test-password-123",
        )

        self.organization = Organization.objects.create(
            name="Delivery Test Organization",
            slug="delivery-test-organization",
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=self.organization,
            role="member",
        )

    def create_message(self, account_type):
        account = EmailAccount.objects.create(
            user=self.user,
            email_address=(
                f"{account_type}-user@oneuch.local"
            ),
            account_type=account_type,
            credential_status="active",
            is_active=True,
        )

        conversation = Conversation.objects.create(
            user=self.user,
            organization=self.organization,
            email_account=account,
            subject="Provider routing test",
            conversation_key=(
                f"provider-routing-{account_type}"
            ),
        )

        message = InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            email_account=account,
            platform=account_type,
            direction="outbound",
            conversation=conversation,
            external_message_id="pending",
            sender=account.email_address,
            recipients="customer@example.com",
            subject="Re: Provider routing test",
            body="Test reply body",
            received_at=timezone.now(),
            is_read=True,
            status="queued",
        )

        return account, message

    @patch("inbox.tasks.send_via_smtp")
    @patch("inbox.tasks.send_outlook_reply")
    @patch("inbox.tasks.send_gmail_reply")
    def test_gmail_reply_uses_gmail_api(
        self,
        gmail_send,
        outlook_send,
        smtp_send,
    ):
        account, message = self.create_message(
            "gmail"
        )

        send_email_task.run(
            account.id,
            "customer@example.com",
            "Re: Provider routing test",
            "Test reply body",
            message.id,
        )

        gmail_send.assert_called_once()

        outlook_send.assert_not_called()
        smtp_send.assert_not_called()

        message.refresh_from_db()

        self.assertEqual(
            message.status,
            "sent",
        )

    @patch("inbox.tasks.send_via_smtp")
    @patch("inbox.tasks.send_outlook_reply")
    @patch("inbox.tasks.send_gmail_reply")
    def test_outlook_reply_uses_microsoft_graph(
        self,
        gmail_send,
        outlook_send,
        smtp_send,
    ):
        account, message = self.create_message(
            "outlook"
        )

        send_email_task.run(
            account.id,
            "customer@example.com",
            "Re: Provider routing test",
            "Test reply body",
            message.id,
        )

        outlook_send.assert_called_once_with(
            user=self.user,
            to_email="customer@example.com",
            subject="Re: Provider routing test",
            body="Test reply body",
        )

        gmail_send.assert_not_called()
        smtp_send.assert_not_called()

        message.refresh_from_db()

        self.assertEqual(
            message.status,
            "sent",
        )

    @patch("inbox.tasks.send_via_smtp")
    @patch("inbox.tasks.send_outlook_reply")
    @patch("inbox.tasks.send_gmail_reply")
    def test_imap_reply_uses_smtp(
        self,
        gmail_send,
        outlook_send,
        smtp_send,
    ):
        account, message = self.create_message(
            "imap"
        )

        send_email_task.run(
            account.id,
            "customer@example.com",
            "Re: Provider routing test",
            "Test reply body",
            message.id,
        )

        smtp_send.assert_called_once()

        gmail_send.assert_not_called()
        outlook_send.assert_not_called()

        message.refresh_from_db()

        self.assertEqual(
            message.status,
            "sent",
        )

    @patch("inbox.tasks.send_outlook_reply")
    def test_outlook_failure_does_not_mark_message_sent(
        self,
        outlook_send,
    ):
        account, message = self.create_message(
            "outlook"
        )

        outlook_send.side_effect = Exception(
            "Microsoft Graph sendMail failed"
        )

        with self.assertRaisesRegex(
            Exception,
            "Microsoft Graph sendMail failed",
        ):
            send_email_task.run(
                account.id,
                "customer@example.com",
                "Re: Provider routing test",
                "Test reply body",
                message.id,
            )

        message.refresh_from_db()

        self.assertEqual(
            message.status,
            "queued",
        )

        self.assertEqual(
            message.retry_count,
            1,
        )

        self.assertIn(
            "Microsoft Graph sendMail failed",
            message.error_reason,
        )

        self.assertNotEqual(
            message.status,
            "sent",
        )
