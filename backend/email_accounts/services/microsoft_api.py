from urllib.parse import (
    quote,
)

import requests

from oauth_tokens.services import (
    get_valid_oauth_token,
)


def _addresses(
    value,
):
    if not value:
        return []


    if isinstance(
        value,
        str,
    ):

        values = (
            value
            .replace(
                ";",
                ",",
            )
            .split(
                ","
            )
        )

    else:

        values = value


    return [
        str(
            item
        )
        .strip()

        for item
        in values

        if str(
            item
        )
        .strip()
    ]


def _graph_recipients(
    value,
):
    return [
        {
            "emailAddress": {
                "address":
                    address
            }
        }

        for address
        in _addresses(
            value
        )
    ]


def send_outlook_reply(
    user,
    to_email,
    subject,
    body,
    *,
    cc_emails=None,
    reply_to_message_id=None,
    reply_mode="reply",
):
    token = (
        get_valid_oauth_token(
            user,
            "microsoft",
        )
    )


    headers = {
        "Authorization":
            (
                "Bearer "
                + token.access_token
            ),

        "Content-Type":
            "application/json",
    }


    if (
        reply_to_message_id
        and
        reply_to_message_id
        not in {
            "pending",
            "sent",
        }
    ):

        operation = (
            "replyAll"
            if reply_mode
            ==
            "reply_all"
            else "reply"
        )


        response = (
            requests.post(
                (
                    "https://graph.microsoft.com/"
                    "v1.0/me/messages/"
                    +
                    quote(
                        reply_to_message_id,
                        safe="",
                    )
                    +
                    "/"
                    +
                    operation
                ),
                headers=headers,
                json={
                    "comment":
                        body
                },
                timeout=30,
            )
        )


    else:

        response = (
            requests.post(
                (
                    "https://graph.microsoft.com/"
                    "v1.0/me/sendMail"
                ),
                headers=headers,
                json={
                    "message": {
                        "subject":
                            subject,

                        "body": {
                            "contentType":
                                "Text",

                            "content":
                                body,
                        },

                        "toRecipients":
                            _graph_recipients(
                                to_email
                            ),

                        "ccRecipients":
                            _graph_recipients(
                                cc_emails
                            ),
                    }
                },
                timeout=30,
            )
        )


    if response.status_code >= 400:

        raise Exception(
            "Microsoft Graph sendMail failed"
        )


    try:

        return (
            response.json()
        )

    except Exception:

        return {}
