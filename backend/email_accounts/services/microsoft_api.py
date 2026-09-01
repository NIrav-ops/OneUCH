import base64

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


def _graph_attachment_payload(
    item,
):
    return {
        "@odata.type":
            "#microsoft.graph.fileAttachment",

        "name":
            item[
                "filename"
            ],

        "contentType":
            item[
                "content_type"
            ],

        "contentBytes":
            (
                base64
                .b64encode(
                    item[
                        "content"
                    ]
                )
                .decode(
                    "ascii"
                )
            ),
    }


def _response_json(
    response,
):
    try:
        return response.json()

    except Exception:
        return {}


def _raise_graph_error(
    response,
    operation,
):
    if (
        response.status_code
        >=
        400
    ):
        raise Exception(
            "Microsoft Graph "
            + operation
            + " failed"
        )


def _send_native_outlook_reply_with_attachments(
    *,
    token,
    reply_to_message_id,
    body,
    reply_mode,
    attachments,
):
    headers = {
        "Authorization":
            (
                "Bearer "
                + token.access_token
            ),

        "Content-Type":
            "application/json",
    }


    operation = (
        "createReplyAll"
        if reply_mode
        ==
        "reply_all"
        else
        "createReply"
    )


    source_id = quote(
        reply_to_message_id,
        safe="",
    )


    create_url = (
        "https://graph.microsoft.com/"
        "v1.0/me/messages/"
        +
        source_id
        +
        "/"
        +
        operation
    )


    create_response = (
        requests.post(
            create_url,
            headers=headers,
            json={
                "comment":
                    body
            },
            timeout=30,
        )
    )


    _raise_graph_error(
        create_response,
        operation,
    )


    draft_id = (
        _response_json(
            create_response
        )
        .get(
            "id"
        )
    )


    if not draft_id:

        raise Exception(
            "Microsoft Graph reply draft did not return an id"
        )


    encoded_draft_id = quote(
        draft_id,
        safe="",
    )


    draft_url = (
        "https://graph.microsoft.com/"
        "v1.0/me/messages/"
        +
        encoded_draft_id
    )


    try:

        for item in attachments:

            attachment_response = (
                requests.post(
                    (
                        draft_url
                        +
                        "/attachments"
                    ),
                    headers=headers,
                    json=(
                        _graph_attachment_payload(
                            item
                        )
                    ),
                    timeout=30,
                )
            )


            _raise_graph_error(
                attachment_response,
                "attachment upload",
            )


        send_response = (
            requests.post(
                (
                    draft_url
                    +
                    "/send"
                ),
                headers=headers,
                timeout=30,
            )
        )


        _raise_graph_error(
            send_response,
            "reply draft send",
        )


    except Exception:

        # Best-effort cleanup. A failed attachment operation must
        # not intentionally leave a One UCH-created reply draft
        # sitting in the user's mailbox.
        try:

            requests.delete(
                draft_url,
                headers=headers,
                timeout=30,
            )

        except Exception:

            pass


        raise


    # The createReply/createReplyAll id belongs to the draft
    # lifecycle. Do not persist it as the final Sent message id.
    #
    # Returning no provider id intentionally causes the existing
    # delivery task to use the "sent" reconciliation placeholder.
    # Outlook Sent synchronization will then replace it with the
    # provider's real Sent-item identity.
    return {}


def send_outlook_reply(
    user,
    to_email,
    subject,
    body,
    *,
    cc_emails=None,
    reply_to_message_id=None,
    reply_mode="reply",
    attachments=None,
):
    token = (
        get_valid_oauth_token(
            user,
            "microsoft",
        )
    )


    attachments = (
        attachments
        or []
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


    native_reply = (
        reply_to_message_id
        and
        reply_to_message_id
        not in {
            "pending",
            "sent",
        }
    )


    # --------------------------------------------------------
    # True threaded Reply / Reply-All with files
    # --------------------------------------------------------

    if (
        native_reply
        and
        attachments
    ):

        return (
            _send_native_outlook_reply_with_attachments(
                token=token,
                reply_to_message_id=(
                    reply_to_message_id
                ),
                body=body,
                reply_mode=reply_mode,
                attachments=attachments,
            )
        )


    # --------------------------------------------------------
    # Existing one-step native Reply / Reply-All
    # --------------------------------------------------------

    if native_reply:

        operation = (
            "replyAll"
            if reply_mode
            ==
            "reply_all"
            else
            "reply"
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


    # --------------------------------------------------------
    # Safe fallback to new-message delivery
    # --------------------------------------------------------

    else:

        graph_message = {
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


        if attachments:

            graph_message[
                "attachments"
            ] = [
                _graph_attachment_payload(
                    item
                )
                for item
                in attachments
            ]


        response = (
            requests.post(
                (
                    "https://graph.microsoft.com/"
                    "v1.0/me/sendMail"
                ),
                headers=headers,
                json={
                    "message":
                        graph_message
                },
                timeout=30,
            )
        )


    if response.status_code >= 400:

        raise Exception(
            "Microsoft Graph sendMail failed"
        )


    return (
        _response_json(
            response
        )
    )
