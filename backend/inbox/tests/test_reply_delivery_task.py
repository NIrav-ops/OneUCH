from unittest.mock import (
    patch,
)

from django.contrib.auth import (
    get_user_model,
)

from django.test import (
    TestCase,
)

from django.utils import (
    timezone,
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

from inbox.tasks import (
    send_email_task,
)


class ReplyDeliveryTaskTests(
    TestCase
):

    def setUp(
        self,
    ):
        User = (
            get_user_model()
        )


        self.user = (
            User.objects.create_user(
                email=(
                    "delivery-user@oneuch.local"
                ),
                password="test-password-123",
            )
        )


        self.organization = (
            Organization.objects.create(
                name=(
                    "Delivery Test Organization"
                ),
                slug=(
                    "delivery-test-organization"
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


    def create_message(
        self,
        account_type,
        *,
        with_cc=False,
    ):
        account = (
            EmailAccount.objects.create(
                user=self.user,
                email_address=(
                    account_type
                    + "-user@oneuch.local"
                ),
                account_type=(
                    account_type
                ),
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
                    account
                ),
                subject=(
                    "Provider routing test"
                ),
                conversation_key=(
                    "provider-routing-"
                    + account_type
                ),
                external_conversation_id=(
                    "provider-thread-1"
                ),
            )
        )


        recipient_meta = {
            "to": [
                {
                    "name":
                        "",

                    "email":
                        "customer@example.com",
                }
            ],

            "cc": (
                [
                    {
                        "name":
                            "",

                        "email":
                            "finance@example.com",
                    }
                ]
                if with_cc
                else []
            ),

            "bcc":
                [],

            "reply_to":
                [],
        }


        message = (
            InboxMessage.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                email_account=(
                    account
                ),
                platform=(
                    account_type
                ),
                direction="outbound",
                folder="outbox",
                conversation=(
                    conversation
                ),
                external_message_id=(
                    "pending"
                ),
                external_conversation_id=(
                    "provider-thread-1"
                ),
                in_reply_to=(
                    "provider-message-1"
                ),
                sender=(
                    account.email_address
                ),
                recipients=(
                    (
                        "customer@example.com, "
                        "finance@example.com"
                    )
                    if with_cc
                    else
                    "customer@example.com"
                ),
                recipient_meta=(
                    recipient_meta
                ),
                subject=(
                    "Re: Provider routing test"
                ),
                body=(
                    "Test reply body"
                ),
                received_at=(
                    timezone.now()
                ),
                is_read=True,
                status="queued",
            )
        )


        return (
            account,
            message,
        )


    @patch(
        "inbox.tasks.send_via_smtp"
    )
    @patch(
        "inbox.tasks.send_outlook_reply"
    )
    @patch(
        "inbox.tasks.send_gmail_reply"
    )
    def test_gmail_reply_uses_structured_provider_context(
        self,
        gmail_send,
        outlook_send,
        smtp_send,
    ):
        account, message = (
            self.create_message(
                "gmail"
            )
        )


        gmail_send.return_value = {
            "id":
                "gmail-sent-id"
        }


        send_email_task.run(
            account.id,
            "customer@example.com",
            "Re: Provider routing test",
            "Test reply body",
            message.id,
        )


        gmail_send.assert_called_once_with(
            user=self.user,
            to_email=(
                "customer@example.com"
            ),
            subject=(
                "Re: Provider routing test"
            ),
            body=(
                "Test reply body"
            ),
            cc_emails=[],
            thread_id=(
                "provider-thread-1"
            ),
            reply_to_message_id=(
                "provider-message-1"
            ),
        )


        outlook_send.assert_not_called()
        smtp_send.assert_not_called()


        message.refresh_from_db()


        self.assertEqual(
            message.status,
            "sent",
        )

        self.assertEqual(
            message.folder,
            "sent",
        )

        self.assertEqual(
            message.external_message_id,
            "gmail-sent-id",
        )


    @patch(
        "inbox.tasks.send_via_smtp"
    )
    @patch(
        "inbox.tasks.send_outlook_reply"
    )
    @patch(
        "inbox.tasks.send_gmail_reply"
    )
    def test_outlook_reply_all_uses_native_reply_all(
        self,
        gmail_send,
        outlook_send,
        smtp_send,
    ):
        account, message = (
            self.create_message(
                "outlook",
                with_cc=True,
            )
        )


        outlook_send.return_value = {}


        send_email_task.run(
            account.id,
            "customer@example.com",
            "Re: Provider routing test",
            "Test reply body",
            message.id,
            "reply_all",
        )


        outlook_send.assert_called_once_with(
            user=self.user,
            to_email=(
                "customer@example.com"
            ),
            subject=(
                "Re: Provider routing test"
            ),
            body=(
                "Test reply body"
            ),
            cc_emails=[
                "finance@example.com"
            ],
            reply_to_message_id=(
                "provider-message-1"
            ),
            reply_mode=(
                "reply_all"
            ),
        )


        gmail_send.assert_not_called()
        smtp_send.assert_not_called()


        message.refresh_from_db()


        self.assertEqual(
            message.status,
            "sent",
        )

        self.assertEqual(
            message.folder,
            "sent",
        )

        self.assertEqual(
            message.external_message_id,
            "sent",
        )


    @patch(
        "inbox.tasks.send_via_smtp"
    )
    @patch(
        "inbox.tasks.send_outlook_reply"
    )
    @patch(
        "inbox.tasks.send_gmail_reply"
    )
    def test_imap_reply_keeps_smtp_compatibility(
        self,
        gmail_send,
        outlook_send,
        smtp_send,
    ):
        account, message = (
            self.create_message(
                "imap",
                with_cc=True,
            )
        )


        send_email_task.run(
            account.id,
            "customer@example.com",
            "Re: Provider routing test",
            "Test reply body",
            message.id,
            "reply_all",
        )


        smtp_send.assert_called_once()


        smtp_to = (
            smtp_send
            .call_args
            .kwargs[
                "to_email"
            ]
        )


        self.assertIn(
            "customer@example.com",
            smtp_to,
        )

        self.assertIn(
            "finance@example.com",
            smtp_to,
        )


        gmail_send.assert_not_called()
        outlook_send.assert_not_called()


    @patch(
        "inbox.tasks.send_outlook_reply"
    )
    def test_outlook_failure_does_not_mark_message_sent(
        self,
        outlook_send,
    ):
        account, message = (
            self.create_message(
                "outlook"
            )
        )


        outlook_send.side_effect = (
            Exception(
                "Microsoft Graph sendMail failed"
            )
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

        self.assertNotEqual(
            message.folder,
            "sent",
        )
