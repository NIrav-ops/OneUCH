import base64

from email.mime.text import (
    MIMEText,
)

import requests

from oauth_tokens.services import (
    get_valid_oauth_token,
)


def _address_header(
    value,
):
    if not value:
        return ""


    if isinstance(
        value,
        str,
    ):
        return (
            value.strip()
        )


    return ", ".join(
        str(
            item
        ).strip()
        for item
        in value
        if str(
            item
        ).strip()
    )


def _gmail_reply_headers(
    *,
    token,
    reply_to_message_id,
):
    if not reply_to_message_id:
        return {}


    response = requests.get(
        (
            "https://gmail.googleapis.com/"
            "gmail/v1/users/me/messages/"
            f"{reply_to_message_id}"
        ),
        headers={
            "Authorization":
                (
                    "Bearer "
                    + token.access_token
                ),
        },
        params=[
            (
                "format",
                "metadata",
            ),
            (
                "metadataHeaders",
                "Message-ID",
            ),
            (
                "metadataHeaders",
                "References",
            ),
        ],
        timeout=30,
    )


    if response.status_code >= 400:
        return {}


    try:

        payload = (
            response.json()
            .get(
                "payload",
                {},
            )
        )

    except Exception:

        return {}


    values = {}


    for header in (
        payload.get(
            "headers",
            [],
        )
        or []
    ):

        name = (
            str(
                header.get(
                    "name",
                    "",
                )
            )
            .strip()
            .lower()
        )


        value = (
            str(
                header.get(
                    "value",
                    "",
                )
            )
            .strip()
        )


        if name and value:

            values[
                name
            ] = value


    return values


def send_gmail_reply(
    user,
    to_email,
    subject,
    body,
    *,
    cc_emails=None,
    thread_id=None,
    reply_to_message_id=None,
):
    token = (
        get_valid_oauth_token(
            user,
            "google",
        )
    )


    message = (
        MIMEText(
            body
        )
    )


    message[
        "To"
    ] = (
        _address_header(
            to_email
        )
    )


    cc_header = (
        _address_header(
            cc_emails
        )
    )


    if cc_header:

        message[
            "Cc"
        ] = (
            cc_header
        )


    message[
        "Subject"
    ] = subject


    provider_headers = (
        _gmail_reply_headers(
            token=token,
            reply_to_message_id=(
                reply_to_message_id
            ),
        )
    )


    original_message_id = (
        provider_headers.get(
            "message-id"
        )
    )


    if original_message_id:

        message[
            "In-Reply-To"
        ] = (
            original_message_id
        )


        existing_references = (
            provider_headers.get(
                "references",
                "",
            )
        )


        references = (
            (
                existing_references
                + " "
                + original_message_id
            )
            .strip()
        )


        message[
            "References"
        ] = references


    raw = (
        base64
        .urlsafe_b64encode(
            message.as_bytes()
        )
        .decode()
    )


    provider_body = {
        "raw":
            raw
    }


    if thread_id:

        provider_body[
            "threadId"
        ] = thread_id


    response = (
        requests.post(
            (
                "https://gmail.googleapis.com/"
                "gmail/v1/users/me/messages/send"
            ),
            headers={
                "Authorization":
                    (
                        "Bearer "
                        + token.access_token
                    ),

                "Content-Type":
                    "application/json",
            },
            json=provider_body,
            timeout=30,
        )
    )


    if response.status_code >= 400:

        raise Exception(
            "Gmail API send failed"
        )


    return response.json()
