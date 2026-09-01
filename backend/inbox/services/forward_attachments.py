import base64
import json

from pathlib import PurePath

from urllib.parse import (
    quote,
)

import requests

from googleapiclient.discovery import (
    build,
)

from googleapis.utils import (
    get_gmail_credentials,
)

from microsoftapis.utils import (
    get_microsoft_access_token,
)

from inbox.services.outbound_attachments import (
    MAX_OUTBOUND_FILES,
    effective_attachment_limit_bytes,
    prepare_outbound_attachments,
)


class ForwardAttachmentProviderError(
    RuntimeError
):
    pass


def _safe_filename(
    value,
):
    filename = (
        PurePath(
            str(
                value
                or
                "attachment"
            )
            .replace(
                "\\",
                "/",
            )
        )
        .name
        .strip()
    )


    return (
        filename
        or
        "attachment"
    )


def _safe_size(
    value,
):
    try:

        result = int(
            value
            or 0
        )

    except (
        TypeError,
        ValueError,
    ):

        result = 0


    return max(
        0,
        result,
    )


def available_forward_source_attachments(
    source,
):
    """
    Build the source-attachment selection presented to the
    user before forwarding.

    If One UCH already owns durable bytes for this message,
    those local Attachment rows are authoritative. This avoids
    downloading our own attachment from the provider again.

    Otherwise provider-native attachment IDs from synchronized
    metadata are used.
    """
    local_records = list(
        source.attachments
        .all()
        .order_by(
            "id"
        )
    )


    if local_records:

        return [
            {
                "key":
                    (
                        "local:"
                        +
                        str(
                            record.id
                        )
                    ),

                "source_type":
                    "local",

                "local_attachment_id":
                    record.id,

                "provider_attachment_id":
                    None,

                "filename":
                    _safe_filename(
                        record.filename
                    ),

                "content_type":
                    (
                        record.content_type
                        or
                        "application/octet-stream"
                    ),

                "size":
                    _safe_size(
                        record.size
                    ),
            }

            for record
            in local_records
        ]


    result = []


    for item in (
        source.attachment_meta
        or []
    ):

        if not isinstance(
            item,
            dict,
        ):
            continue


        attachment_id = (
            str(
                item.get(
                    "attachment_id"
                )
                or ""
            )
            .strip()
        )


        # Unsynchronized outbound metadata can legitimately
        # contain attachment_id=None. It is not safe to invent
        # or guess a provider attachment identifier.
        if not attachment_id:
            continue


        result.append(
            {
                "key":
                    (
                        "provider:"
                        +
                        attachment_id
                    ),

                "source_type":
                    "provider",

                "local_attachment_id":
                    None,

                "provider_attachment_id":
                    attachment_id,

                "filename":
                    _safe_filename(
                        item.get(
                            "filename"
                        )
                    ),

                "content_type":
                    (
                        str(
                            item.get(
                                "mime_type"
                            )
                            or
                            "application/octet-stream"
                        )
                        .strip()
                    ),

                "size":
                    _safe_size(
                        item.get(
                            "size"
                        )
                    ),
            }
        )


    return result


def serialize_forward_source_attachments(
    source,
):
    return [
        {
            "key":
                item[
                    "key"
                ],

            "filename":
                item[
                    "filename"
                ],

            "content_type":
                item[
                    "content_type"
                ],

            "size":
                item[
                    "size"
                ],

            "source_type":
                item[
                    "source_type"
                ],

            "selected":
                True,
        }

        for item
        in available_forward_source_attachments(
            source
        )
    ]


def _parse_source_attachment_keys(
    *,
    data,
    available,
):
    """
    Missing selector means normal mail-client behavior:
    forward all available original attachments.

    An explicitly supplied [] means the user removed all
    inherited attachments.
    """
    available_by_key = {
        item[
            "key"
        ]:
            item
        for item
        in available
    }


    if (
        "source_attachment_keys"
        not in data
    ):

        return list(
            available
        )


    raw = data.get(
        "source_attachment_keys"
    )


    if raw in (
        None,
        "",
    ):

        values = []

    elif isinstance(
        raw,
        (
            list,
            tuple,
        ),
    ):

        values = list(
            raw
        )

    else:

        text = str(
            raw
        ).strip()


        if not text:

            values = []

        else:

            try:

                decoded = json.loads(
                    text
                )

            except json.JSONDecodeError:

                decoded = [
                    value.strip()
                    for value
                    in text.split(
                        ","
                    )
                    if value.strip()
                ]


            if isinstance(
                decoded,
                list,
            ):

                values = decoded

            else:

                values = [
                    decoded
                ]


    normalized = []


    for value in values:

        key = (
            str(
                value
                or ""
            )
            .strip()
        )


        if not key:
            continue


        if key not in available_by_key:

            raise ValueError(
                "A selected original attachment does not "
                "belong to this source message."
            )


        if key not in normalized:

            normalized.append(
                key
            )


    return [
        available_by_key[
            key
        ]
        for key
        in normalized
    ]


def _load_local_attachment(
    *,
    source,
    descriptor,
):
    attachment = (
        source.attachments
        .filter(
            id=descriptor[
                "local_attachment_id"
            ]
        )
        .first()
    )


    if attachment is None:

        raise ValueError(
            "Original local attachment is no longer available."
        )


    try:

        attachment.file.open(
            "rb"
        )


        try:

            content = (
                attachment.file.read()
            )

        finally:

            attachment.file.close()

    except Exception as exc:

        raise ValueError(
            "Original local attachment content is unavailable."
        ) from exc


    if not content:

        raise ValueError(
            "Original attachment is empty."
        )


    return content


def _load_gmail_attachment(
    *,
    user,
    source,
    attachment_id,
):
    provider_message_id = (
        str(
            source.external_message_id
            or ""
        )
        .strip()
    )


    if provider_message_id in {
        "",
        "pending",
        "sent",
    }:

        raise ForwardAttachmentProviderError(
            "Original Gmail message is not synchronized yet."
        )


    try:

        credentials = (
            get_gmail_credentials(
                user
            )
        )


        service = build(
            "gmail",
            "v1",
            credentials=credentials,
        )


        result = (
            service.users()
            .messages()
            .attachments()
            .get(
                userId="me",
                messageId=(
                    provider_message_id
                ),
                id=(
                    attachment_id
                ),
            )
            .execute()
        )


        encoded = (
            result.get(
                "data"
            )
        )


        if not encoded:

            raise ForwardAttachmentProviderError(
                "Original Gmail attachment content is missing."
            )


        padding = (
            "="
            *
            (
                (
                    4
                    -
                    len(
                        encoded
                    )
                    %
                    4
                )
                %
                4
            )
        )


        return (
            base64
            .urlsafe_b64decode(
                (
                    encoded
                    +
                    padding
                )
                .encode(
                    "utf-8"
                )
            )
        )


    except ForwardAttachmentProviderError:

        raise


    except Exception as exc:

        raise ForwardAttachmentProviderError(
            "Unable to load original Gmail attachment."
        ) from exc


def _load_outlook_attachment(
    *,
    user,
    source,
    attachment_id,
):
    provider_message_id = (
        str(
            source.external_message_id
            or ""
        )
        .strip()
    )


    if provider_message_id in {
        "",
        "pending",
        "sent",
    }:

        raise ForwardAttachmentProviderError(
            "Original Microsoft message is not synchronized yet."
        )


    try:

        token = (
            get_microsoft_access_token(
                user
            )
        )


        response = requests.get(
            (
                "https://graph.microsoft.com/"
                "v1.0/me/messages/"
                +
                quote(
                    provider_message_id,
                    safe="",
                )
                +
                "/attachments/"
                +
                quote(
                    str(
                        attachment_id
                    ),
                    safe="",
                )
            ),
            headers={
                "Authorization":
                    f"Bearer {token}"
            },
            timeout=30,
        )


        if response.status_code != 200:

            raise ForwardAttachmentProviderError(
                "Unable to load original Microsoft attachment "
                f"(HTTP {response.status_code})."
            )


        payload = (
            response.json()
        )


        encoded = (
            payload.get(
                "contentBytes"
            )
        )


        if not encoded:

            raise ForwardAttachmentProviderError(
                "Original Microsoft attachment content is missing."
            )


        return base64.b64decode(
            encoded
        )


    except ForwardAttachmentProviderError:

        raise


    except Exception as exc:

        raise ForwardAttachmentProviderError(
            "Unable to load original Microsoft attachment."
        ) from exc


def _load_source_descriptor(
    *,
    user,
    source,
    descriptor,
):
    if (
        descriptor[
            "source_type"
        ]
        ==
        "local"
    ):

        content = (
            _load_local_attachment(
                source=source,
                descriptor=descriptor,
            )
        )


    elif source.platform == "gmail":

        content = (
            _load_gmail_attachment(
                user=user,
                source=source,
                attachment_id=(
                    descriptor[
                        "provider_attachment_id"
                    ]
                ),
            )
        )


    elif source.platform == "outlook":

        content = (
            _load_outlook_attachment(
                user=user,
                source=source,
                attachment_id=(
                    descriptor[
                        "provider_attachment_id"
                    ]
                ),
            )
        )


    else:

        raise ValueError(
            "Automatic original attachment forwarding "
            "is not supported for this provider."
        )


    if not content:

        raise ValueError(
            "Original attachment is empty."
        )


    return {
        "filename":
            descriptor[
                "filename"
            ],

        "content_type":
            descriptor[
                "content_type"
            ],

        "size":
            len(
                content
            ),

        "content":
            content,

        "forwarded_original":
            True,

        "source_attachment_key":
            descriptor[
                "key"
            ],
    }


def prepare_forward_attachments(
    *,
    request,
    source,
    account,
):
    """
    Merge inherited source attachments and newly uploaded files.

    Security/correctness:
    - source IDs are resolved only from this source message
    - missing selector => all originals
    - explicit [] => user removed all originals
    - aggregate provider/org count+size limits are enforced
    - provider bytes are fetched only after selector validation
    """
    available = (
        available_forward_source_attachments(
            source
        )
    )


    selected = (
        _parse_source_attachment_keys(
            data=request.data,
            available=available,
        )
    )


    user_added = (
        prepare_outbound_attachments(
            request=request,
            account=account,
        )
    )


    combined_count = (
        len(
            selected
        )
        +
        len(
            user_added
        )
    )


    if combined_count > MAX_OUTBOUND_FILES:

        raise ValueError(
            "A maximum of 10 attachments can be sent at once."
        )


    # Reject known oversize selections before provider downloads
    # when metadata already gives us enough information.
    limit = (
        effective_attachment_limit_bytes(
            account=account,
            user=request.user,
        )
    )


    known_selected_size = sum(
        int(
            item.get(
                "size",
                0,
            )
            or 0
        )
        for item
        in selected
    )


    user_size = sum(
        int(
            item.get(
                "size",
                0,
            )
            or 0
        )
        for item
        in user_added
    )


    if (
        known_selected_size
        and
        known_selected_size
        +
        user_size
        >
        limit
    ):

        limit_mb = (
            limit
            /
            (
                1024
                *
                1024
            )
        )


        raise ValueError(
            "Attachments exceed the "
            f"{limit_mb:g} MB outbound limit "
            f"for {account.email_address}."
        )


    inherited = [
        _load_source_descriptor(
            user=request.user,
            source=source,
            descriptor=descriptor,
        )

        for descriptor
        in selected
    ]


    combined = [
        *inherited,
        *user_added,
    ]


    actual_size = sum(
        int(
            item.get(
                "size",
                0,
            )
            or 0
        )
        for item
        in combined
    )


    if actual_size > limit:

        limit_mb = (
            limit
            /
            (
                1024
                *
                1024
            )
        )


        raise ValueError(
            "Attachments exceed the "
            f"{limit_mb:g} MB outbound limit "
            f"for {account.email_address}."
        )


    return {
        "attachments":
            combined,

        "source_attachment_count":
            len(
                available
            ),

        "source_attachments_forwarded":
            len(
                inherited
            ),

        "user_attachment_count":
            len(
                user_added
            ),
    }
