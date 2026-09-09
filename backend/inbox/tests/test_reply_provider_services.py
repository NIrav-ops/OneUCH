
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

from email_accounts.services.microsoft_api import (
    send_outlook_reply,
)


class ReplyProviderServiceTests(
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
    def test_gmail_reply_preserves_thread_headers_and_cc(
        self,
        mocked_token,
        mocked_get,
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


        metadata = (
            MagicMock()
        )

        metadata.status_code = 200

        metadata.json.return_value = {
            "payload": {
                "headers": [
                    {
                        "name":
                            "Message-ID",

                        "value":
                            "<original@example.com>",
                    },
                    {
                        "name":
                            "References",

                        "value":
                            "<older@example.com>",
                    },
                ]
            }
        }

        mocked_get.return_value = (
            metadata
        )


        sent = (
            MagicMock()
        )

        sent.status_code = 200

        sent.json.return_value = {
            "id":
                "gmail-new-message"
        }

        mocked_post.return_value = (
            sent
        )


        result = (
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
                thread_id=(
                    "gmail-thread-1"
                ),
                reply_to_message_id=(
                    "gmail-message-1"
                ),
            )
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
            "gmail-thread-1",
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
            mime[
                "To"
            ],
            "customer@example.com",
        )

        self.assertEqual(
            mime[
                "Cc"
            ],
            "finance@example.com",
        )

        self.assertEqual(
            mime[
                "In-Reply-To"
            ],
            "<original@example.com>",
        )

        self.assertIn(
            "<older@example.com>",
            mime[
                "References"
            ],
        )

        self.assertIn(
            "<original@example.com>",
            mime[
                "References"
            ],
        )

        self.assertEqual(
            result[
                "id"
            ],
            "gmail-new-message",
        )


    @patch(
        "email_accounts.services.microsoft_api."
        "requests.patch"
    )
    @patch(
        "email_accounts.services.microsoft_api."
        "requests.post"
    )
    @patch(
        "email_accounts.services.microsoft_api."
        "get_valid_oauth_token"
    )
    def test_outlook_reply_all_uses_draft_and_exact_recipients(
        self,
        mocked_token,
        mocked_post,
        mocked_patch,
    ):
        token = (
            MagicMock()
        )

        token.access_token = (
            "microsoft-token"
        )

        mocked_token.return_value = (
            token
        )


        created = (
            MagicMock()
        )

        created.status_code = 201

        created.json.return_value = {
            "id":
                "reply-draft-1"
        }


        sent = (
            MagicMock()
        )

        sent.status_code = 202

        sent.json.side_effect = (
            ValueError()
        )


        mocked_post.side_effect = [
            created,
            sent,
        ]


        patched = (
            MagicMock()
        )

        patched.status_code = 200

        mocked_patch.return_value = (
            patched
        )


        result = (
            send_outlook_reply(
                user=object(),
                to_email=(
                    "customer@example.com"
                ),
                subject=(
                    "Re: Test"
                ),
                body="Reply body",
                cc_emails=[
                    "finance@example.com"
                ],
                bcc_emails=[
                    "audit@example.com"
                ],
                reply_to_message_id=(
                    "graph-message-1"
                ),
                reply_mode="reply_all",
            )
        )


        create_call = (
            mocked_post
            .call_args_list[0]
        )

        self.assertTrue(
            create_call.args[
                0
            ].endswith(
                (
                    "/messages/"
                    "graph-message-1/"
                    "createReplyAll"
                )
            )
        )


        self.assertEqual(
            create_call.kwargs[
                "json"
            ],
            {
                "comment":
                    "Reply body"
            },
        )


        patch_call = (
            mocked_patch
            .call_args
        )


        self.assertTrue(
            patch_call.args[
                0
            ].endswith(
                "/messages/reply-draft-1"
            )
        )


        self.assertEqual(
            patch_call.kwargs[
                "json"
            ],
            {
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address":
                                "customer@example.com"
                        }
                    }
                ],

                "ccRecipients": [
                    {
                        "emailAddress": {
                            "address":
                                "finance@example.com"
                        }
                    }
                ],

                "bccRecipients": [
                    {
                        "emailAddress": {
                            "address":
                                "audit@example.com"
                        }
                    }
                ],
            },
        )


        send_call = (
            mocked_post
            .call_args_list[1]
        )


        self.assertTrue(
            send_call.args[
                0
            ].endswith(
                "/messages/reply-draft-1/send"
            )
        )


        self.assertEqual(
            result,
            {},
        )
