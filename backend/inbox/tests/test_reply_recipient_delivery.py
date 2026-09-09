import base64

from email import (
    message_from_bytes,
)

from unittest.mock import (
    MagicMock,
    patch,
)

from django.test import (
    SimpleTestCase,
)

from email_accounts.services.gmail_api import (
    send_gmail_reply,
)

from inbox.tasks import (
    _deliver_reply_message,
)


def recipient_message():
    message = (
        MagicMock()
    )

    message.recipient_meta = {
        "to": [
            {
                "name":
                    "Customer",

                "email":
                    "customer@example.com",
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
                    "Audit",

                "email":
                    "audit@example.com",
            }
        ],

        "reply_to":
            [],
    }

    message.external_conversation_id = (
        "provider-thread-1"
    )

    message.in_reply_to = (
        "provider-message-1"
    )

    return message


class ReplyRecipientDeliveryContractTests(
    SimpleTestCase
):

    def test_delivery_task_passes_bcc_to_gmail(
        self,
    ):
        account = (
            MagicMock()
        )

        account.account_type = (
            "gmail"
        )

        account.user = object()


        message = (
            recipient_message()
        )


        with patch(
            "inbox.tasks."
            "load_persisted_outbound_attachments",
            return_value=[],
        ), patch(
            "inbox.tasks."
            "send_gmail_reply"
        ) as gmail_send:

            _deliver_reply_message(
                email_account=account,
                inbox_message=message,
                fallback_to=(
                    "customer@example.com"
                ),
                subject="Re: Test",
                body="Body",
            )


        kwargs = (
            gmail_send
            .call_args
            .kwargs
        )


        self.assertEqual(
            kwargs[
                "to_email"
            ],
            "customer@example.com",
        )

        self.assertEqual(
            kwargs[
                "cc_emails"
            ],
            [
                "finance@example.com"
            ],
        )

        self.assertEqual(
            kwargs[
                "bcc_emails"
            ],
            [
                "audit@example.com"
            ],
        )


    def test_delivery_task_passes_bcc_to_outlook(
        self,
    ):
        account = (
            MagicMock()
        )

        account.account_type = (
            "outlook"
        )

        account.user = object()


        message = (
            recipient_message()
        )


        with patch(
            "inbox.tasks."
            "load_persisted_outbound_attachments",
            return_value=[],
        ), patch(
            "inbox.tasks."
            "send_outlook_reply"
        ) as outlook_send:

            _deliver_reply_message(
                email_account=account,
                inbox_message=message,
                fallback_to=(
                    "customer@example.com"
                ),
                subject="Re: Test",
                body="Body",
                reply_mode="reply_all",
            )


        kwargs = (
            outlook_send
            .call_args
            .kwargs
        )


        self.assertEqual(
            kwargs[
                "cc_emails"
            ],
            [
                "finance@example.com"
            ],
        )

        self.assertEqual(
            kwargs[
                "bcc_emails"
            ],
            [
                "audit@example.com"
            ],
        )

        self.assertEqual(
            kwargs[
                "reply_mode"
            ],
            "reply_all",
        )


    def test_delivery_task_passes_bcc_to_smtp_envelope(
        self,
    ):
        account = (
            MagicMock()
        )

        account.account_type = (
            "imap"
        )

        account.is_credential_valid.return_value = (
            True
        )

        account.get_credential.return_value = (
            "synthetic-password"
        )


        message = (
            recipient_message()
        )


        with patch(
            "inbox.tasks."
            "load_persisted_outbound_attachments",
            return_value=[],
        ), patch(
            "inbox.tasks."
            "send_via_smtp"
        ) as smtp_send:

            _deliver_reply_message(
                email_account=account,
                inbox_message=message,
                fallback_to=(
                    "customer@example.com"
                ),
                subject="Re: Test",
                body="Body",
                reply_mode="reply_all",
            )


        kwargs = (
            smtp_send
            .call_args
            .kwargs
        )


        self.assertEqual(
            [
                item["email"]
                for item
                in kwargs[
                    "to_emails"
                ]
            ],
            [
                "customer@example.com"
            ],
        )

        self.assertEqual(
            [
                item["email"]
                for item
                in kwargs[
                    "cc_emails"
                ]
            ],
            [
                "finance@example.com"
            ],
        )

        self.assertEqual(
            [
                item["email"]
                for item
                in kwargs[
                    "bcc_emails"
                ]
            ],
            [
                "audit@example.com"
            ],
        )


    @patch(
        "email_accounts.services.gmail_api."
        "requests.post"
    )
    @patch(
        "email_accounts.services.gmail_api."
        "get_valid_oauth_token"
    )
    def test_gmail_mime_contains_explicit_bcc(
        self,
        mocked_token,
        mocked_post,
    ):
        token = (
            MagicMock()
        )

        token.access_token = (
            "google-token"
        )

        mocked_token.return_value = (
            token
        )


        response = (
            MagicMock()
        )

        response.status_code = 200

        response.json.return_value = {
            "id":
                "gmail-recipient-test"
        }

        mocked_post.return_value = (
            response
        )


        send_gmail_reply(
            user=object(),
            to_email=(
                "customer@example.com"
            ),
            subject="Re: Test",
            body="Body",
            cc_emails=[
                "finance@example.com"
            ],
            bcc_emails=[
                "audit@example.com"
            ],
        )


        provider_body = (
            mocked_post
            .call_args
            .kwargs[
                "json"
            ]
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


        self.assertEqual(
            mime["To"],
            "customer@example.com",
        )

        self.assertEqual(
            mime["Cc"],
            "finance@example.com",
        )

        self.assertEqual(
            mime["Bcc"],
            "audit@example.com",
        )
