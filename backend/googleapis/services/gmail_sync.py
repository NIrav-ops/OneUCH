import base64

from datetime import (
    datetime,
    timezone as datetime_timezone,
)

from email.header import (
    decode_header,
    make_header,
)

from email.message import (
    Message,
)

from email.utils import (
    getaddresses,
)

from html import (
    unescape,
)

from html.parser import (
    HTMLParser,
)


from asgiref.sync import (
    async_to_sync,
)

from channels.layers import (
    get_channel_layer,
)

from googleapiclient.discovery import (
    build,
)


from inbox.models import (
    Conversation,
    InboxMessage,
)

from inbox.services.conversation_cache import (
    invalidate_conversation_cache,
)

from inbox.services.mail_sync_policy import (
    GMAIL_PAGE_SIZE,
    mark_initial_history_complete,
    resolve_mail_sync_window,
)

from inbox.services.mail_mutations import (
    refresh_conversation_local_state,
)

from inbox.services.sync_status import (
    update_sync_status,
)

from googleapis.utils import (
    get_gmail_credentials,
)

from knowledge.services.message_processor import (
    MessageProcessor,
)

from platform_core.observability.logger import (
    get_logger,
    log_event,
)


logger = get_logger(
    "oneuch.runtime.gmail"
)


# ============================================================
# TEXT / HEADER NORMALIZATION
# ============================================================

class _HTMLTextExtractor(
    HTMLParser
):

    def __init__(
        self,
    ):
        super().__init__()

        self.parts = []


    def handle_data(
        self,
        data,
    ):
        value = str(
            data or ""
        ).strip()

        if value:
            self.parts.append(
                value
            )


    def text(
        self,
    ):
        return "\n".join(
            self.parts
        ).strip()


def _decode_header_value(
    value,
):
    source = str(
        value or ""
    )

    if not source:
        return ""

    try:
        return str(
            make_header(
                decode_header(
                    source
                )
            )
        )

    except Exception:
        return source


def _header_values(
    headers,
    name,
):
    target = (
        str(name)
        .lower()
    )

    return [
        _decode_header_value(
            header.get(
                "value",
                "",
            )
        )
        for header in (
            headers or []
        )
        if (
            str(
                header.get(
                    "name",
                    "",
                )
            ).lower()
            ==
            target
        )
    ]


def _first_header(
    headers,
    name,
):
    values = (
        _header_values(
            headers,
            name,
        )
    )

    return (
        values[0]
        if values
        else ""
    )


def _normalize_addresses(
    values,
):
    addresses = []

    seen = set()


    for (
        display_name,
        email_address,
    ) in getaddresses(
        [
            str(value)
            for value in (
                values or []
            )
            if value
        ]
    ):

        email_value = (
            str(
                email_address
                or ""
            )
            .strip()
            .lower()
        )

        if (
            not email_value
            or
            email_value in seen
        ):
            continue


        seen.add(
            email_value
        )


        addresses.append(
            {
                "name":
                    _decode_header_value(
                        display_name
                    ).strip(),

                "email":
                    email_value,
            }
        )


    return addresses


def _flatten_recipient_emails(
    recipient_meta,
):
    values = []

    seen = set()


    for key in (
        "to",
        "cc",
        "bcc",
    ):

        for item in (
            recipient_meta.get(
                key,
                [],
            )
            or []
        ):

            email_value = (
                str(
                    item.get(
                        "email",
                        "",
                    )
                )
                .strip()
                .lower()
            )

            if (
                not email_value
                or
                email_value in seen
            ):
                continue


            seen.add(
                email_value
            )

            values.append(
                email_value
            )


    return ", ".join(
        values
    )


def _message_identities(
    headers,
):
    sender_candidates = (
        _normalize_addresses(
            _header_values(
                headers,
                "from",
            )
        )
    )

    sender_meta = (
        sender_candidates[0]
        if sender_candidates
        else {}
    )


    recipient_meta = {
        "to":
            _normalize_addresses(
                _header_values(
                    headers,
                    "to",
                )
            ),

        "cc":
            _normalize_addresses(
                _header_values(
                    headers,
                    "cc",
                )
            ),

        "bcc":
            _normalize_addresses(
                _header_values(
                    headers,
                    "bcc",
                )
            ),

        "reply_to":
            _normalize_addresses(
                _header_values(
                    headers,
                    "reply-to",
                )
            ),
    }


    return (
        sender_meta,
        recipient_meta,
    )


# ============================================================
# GMAIL BODY NORMALIZATION
# ============================================================

def _content_charset(
    headers,
):
    content_type = (
        _first_header(
            headers,
            "content-type",
        )
    )

    if not content_type:
        return "utf-8"


    message = Message()

    message[
        "content-type"
    ] = content_type


    return (
        message.get_content_charset()
        or "utf-8"
    )


def _decode_body_data(
    data,
    *,
    charset="utf-8",
):
    if not data:
        return ""


    raw = str(
        data
    )


    padding = (
        "="
        *
        (
            (
                4
                - len(raw) % 4
            )
            % 4
        )
    )


    try:

        decoded = (
            base64.urlsafe_b64decode(
                raw + padding
            )
        )

    except Exception:

        return ""


    try:

        return decoded.decode(
            charset
        )

    except (
        LookupError,
        UnicodeDecodeError,
    ):

        return decoded.decode(
            "utf-8",
            errors="replace",
        )


def _iter_payload_parts(
    payload,
):
    yield payload


    for child in (
        payload.get(
            "parts",
            [],
        )
        or []
    ):

        yield from (
            _iter_payload_parts(
                child
            )
        )


def _is_attachment_part(
    part,
):
    if (
        part.get(
            "filename"
        )
    ):
        return True


    disposition = (
        _first_header(
            part.get(
                "headers",
                [],
            ),
            "content-disposition",
        )
        .lower()
    )


    return disposition.startswith(
        "attachment"
    )


def _html_to_text(
    value,
):
    parser = (
        _HTMLTextExtractor()
    )

    try:

        parser.feed(
            str(
                value or ""
            )
        )

        parser.close()


        return unescape(
            parser.text()
        )

    except Exception:

        return unescape(
            str(
                value or ""
            )
        )


def extract_gmail_body(
    payload,
    *,
    snippet="",
):
    plain_parts = []

    html_parts = []


    for part in (
        _iter_payload_parts(
            payload or {}
        )
    ):

        if _is_attachment_part(
            part
        ):
            continue


        mime_type = (
            str(
                part.get(
                    "mimeType",
                    "",
                )
            )
            .lower()
        )


        if mime_type not in {
            "text/plain",
            "text/html",
        }:
            continue


        text = (
            _decode_body_data(
                (
                    part.get(
                        "body",
                        {},
                    )
                    or {}
                ).get(
                    "data"
                ),
                charset=(
                    _content_charset(
                        part.get(
                            "headers",
                            [],
                        )
                    )
                ),
            )
        ).strip()


        if not text:
            continue


        if mime_type == "text/plain":

            plain_parts.append(
                text
            )

        else:

            html_parts.append(
                text
            )


    if plain_parts:

        return "\n\n".join(
            plain_parts
        ).strip()


    if html_parts:

        return "\n\n".join(
            _html_to_text(
                value
            )
            for value in html_parts
        ).strip()


    return str(
        snippet or ""
    ).strip()


# ============================================================
# ATTACHMENT METADATA
# ============================================================

def extract_attachments(
    payload,
):
    attachments = []


    for part in (
        _iter_payload_parts(
            payload or {}
        )
    ):

        filename = (
            part.get(
                "filename"
            )
        )

        if not filename:
            continue


        body = (
            part.get(
                "body",
                {},
            )
            or {}
        )


        if (
            body.get(
                "attachmentId"
            )
            or
            body.get(
                "data"
            )
        ):

            attachments.append(
                {
                    "filename":
                        filename,

                    "attachment_id":
                        body.get(
                            "attachmentId"
                        ),

                    "mime_type":
                        part.get(
                            "mimeType"
                        ),
                }
            )


    return attachments


# ============================================================
# PROVIDER PAGINATION
# ============================================================

def _gmail_query(
    cutoff,
):
    # Gmail's search query uses date granularity here.
    # Incremental sync deliberately includes a one-day overlap
    # and provider message IDs enforce idempotency.
    date_value = (
        cutoff.strftime(
            "%Y/%m/%d"
        )
    )


    return (
        f"after:{date_value} "
        "{in:inbox in:sent}"
    )


def _iter_gmail_message_references(
    *,
    service,
    cutoff,
):
    page_token = None


    while True:

        kwargs = {
            "userId":
                "me",

            "q":
                _gmail_query(
                    cutoff
                ),

            "maxResults":
                GMAIL_PAGE_SIZE,
        }


        if page_token:

            kwargs[
                "pageToken"
            ] = page_token


        result = (
            service
            .users()
            .messages()
            .list(
                **kwargs
            )
            .execute()
        )


        for reference in (
            result.get(
                "messages",
                [],
            )
            or []
        ):

            yield reference


        page_token = (
            result.get(
                "nextPageToken"
            )
        )


        if not page_token:
            break


# ============================================================
# CONVERSATION MATERIALIZATION
# ============================================================

def _resolve_conversation(
    *,
    user,
    organization,
    email_account,
    thread_id,
    subject,
):
    conversation_key = (
        f"gmail_{thread_id}"
    )


    conversation = (
        Conversation.objects
        .filter(
            user=user,
            conversation_key=(
                conversation_key
            ),
        )
        .first()
    )


    if conversation is None:

        conversation = (
            Conversation.objects.create(
                user=user,
                organization=(
                    organization
                ),
                email_account=(
                    email_account
                ),
                conversation_key=(
                    conversation_key
                ),
                external_conversation_id=(
                    thread_id
                ),
                subject=(
                    subject
                    or "No Subject"
                ),
            )
        )

        return conversation


    changed = []


    if (
        conversation
        .email_account_id
        !=
        email_account.id
    ):

        conversation.email_account = (
            email_account
        )

        changed.append(
            "email_account"
        )


    if (
        conversation
        .organization_id
        !=
        organization.id
    ):

        conversation.organization = (
            organization
        )

        changed.append(
            "organization"
        )


    if (
        not conversation
        .external_conversation_id
    ):

        conversation.external_conversation_id = (
            thread_id
        )

        changed.append(
            "external_conversation_id"
        )


    if changed:

        conversation.save(
            update_fields=changed
        )


    return conversation


def _update_conversation_if_newer(
    *,
    conversation,
    message,
):
    if (
        conversation.last_message_at
        is not None
        and
        message.received_at
        <
        conversation.last_message_at
    ):

        return


    conversation.last_message = (
        message
    )

    conversation.last_message_at = (
        message.received_at
    )

    conversation.last_message_preview = (
        message.body[:120]
        if message.body
        else "No preview"
    )

    conversation.subject = (
        message.subject
        or conversation.subject
    )


    if (
        message.direction
        ==
        "inbound"
    ):

        conversation.unread_count = (
            InboxMessage.objects
            .filter(
                conversation=(
                    conversation
                ),
                is_read=False,
                direction="inbound",
            )
            .count()
        )


    conversation.save(
        update_fields=[
            "last_message",
            "last_message_at",
            "last_message_preview",
            "subject",
            "unread_count",
        ]
    )


# ============================================================
# GMAIL INGESTION
# ============================================================

def _fetch_gmail_emails_impl(
    *,
    user,
    email_account,
    limit=None,
):
    # `limit` remains accepted for backwards compatibility
    # with older callers/tests. P1A intentionally performs
    # complete provider pagination for the resolved sync window.
    del limit


    credentials = (
        get_gmail_credentials(
            user
        )
    )


    service = (
        build(
            "gmail",
            "v1",
            credentials=(
                credentials
            ),
        )
    )


    window = (
        resolve_mail_sync_window(
            email_account=(
                email_account
            )
        )
    )


    organization = (
        user
        .organization_membership
        .organization
    )


    processed_count = 0

    created_count = 0

    upgraded_count = 0

    skipped_count = 0

    failed_count = 0


    for reference in (
        _iter_gmail_message_references(
            service=service,
            cutoff=window.cutoff,
        )
    ):

        try:

            provider_id = (
                reference.get(
                    "id"
                )
            )


            if not provider_id:

                failed_count += 1

                continue


            existing = (
                InboxMessage.objects
                .filter(
                    user=user,
                    email_account=(
                        email_account
                    ),
                    external_message_id=(
                        provider_id
                    ),
                )
                .first()
            )


            message = (
                service
                .users()
                .messages()
                .get(
                    userId="me",
                    id=provider_id,
                    format="full",
                )
                .execute()
            )


            if (
                existing
                and
                not window.initial_history
            ):

                label_ids = set(
                    message.get(
                        "labelIds",
                        [],
                    )
                    or []
                )


                if "SENT" in label_ids:

                    existing.direction = (
                        "outbound"
                    )

                    existing.folder = (
                        "sent"
                    )


                elif "INBOX" in label_ids:

                    existing.direction = (
                        "inbound"
                    )

                    existing.folder = (
                        "inbox"
                    )


                existing.external_conversation_id = (
                    message.get(
                        "threadId"
                    )
                    or
                    existing.external_conversation_id
                )

                existing.is_read = (
                    "UNREAD"
                    not in label_ids
                )

                existing.is_starred = (
                    "STARRED"
                    in label_ids
                )


                existing.save(
                    update_fields=[
                        "direction",
                        "folder",
                        "external_conversation_id",
                        "is_read",
                        "is_starred",
                    ]
                )


                refresh_conversation_local_state(
                    existing.conversation
                )


                skipped_count += 1


                log_event(
                    logger,
                    "debug",
                    (
                        "gmail.message."
                        "refreshed_mutable_state"
                    ),
                    provider="gmail",
                    account_id=(
                        email_account.id
                    ),
                    message_id=(
                        existing.id
                    ),
                )


                continue


            processed_count += 1


            payload = (
                message.get(
                    "payload",
                    {},
                )
                or {}
            )


            headers = (
                payload.get(
                    "headers",
                    [],
                )
                or []
            )


            subject = (
                _first_header(
                    headers,
                    "subject",
                )
                or
                message.get(
                    "snippet",
                    "",
                )
                or
                "No Subject"
            )


            (
                sender_meta,
                recipient_meta,
            ) = (
                _message_identities(
                    headers
                )
            )


            sender = (
                sender_meta.get(
                    "email",
                    "",
                )
            )


            recipients = (
                _flatten_recipient_emails(
                    recipient_meta
                )
            )


            label_ids = set(
                message.get(
                    "labelIds",
                    [],
                )
                or []
            )


            if "SENT" in label_ids:

                direction = (
                    "outbound"
                )

                folder = (
                    "sent"
                )

            elif "INBOX" in label_ids:

                direction = (
                    "inbound"
                )

                folder = (
                    "inbox"
                )

            else:

                # The provider query is deliberately limited to
                # Inbox/Sent. Ignore a stale/non-matching result
                # rather than creating an incorrect folder.
                continue


            thread_id = (
                message.get(
                    "threadId"
                )
                or provider_id
            )


            internal_date = int(
                message.get(
                    "internalDate",
                    0,
                )
                or 0
            )


            if internal_date <= 0:

                raise RuntimeError(
                    "Gmail message does not "
                    "contain a valid internalDate."
                )


            received_at = (
                datetime.fromtimestamp(
                    (
                        internal_date
                        / 1000
                    ),
                    tz=(
                        datetime_timezone.utc
                    ),
                )
            )


            body = (
                extract_gmail_body(
                    payload,
                    snippet=(
                        message.get(
                            "snippet",
                            "",
                        )
                    ),
                )
            )


            attachments = (
                extract_attachments(
                    payload
                )
            )


            conversation = (
                _resolve_conversation(
                    user=user,
                    organization=(
                        organization
                    ),
                    email_account=(
                        email_account
                    ),
                    thread_id=(
                        thread_id
                    ),
                    subject=subject,
                )
            )


            if existing:

                message_obj = (
                    existing
                )


                message_obj.organization = (
                    organization
                )

                message_obj.email_account = (
                    email_account
                )

                message_obj.conversation = (
                    conversation
                )

                message_obj.platform = (
                    "gmail"
                )

                message_obj.direction = (
                    direction
                )

                message_obj.folder = (
                    folder
                )

                message_obj.external_conversation_id = (
                    thread_id
                )

                message_obj.sender = (
                    sender
                )

                message_obj.recipients = (
                    recipients
                )

                message_obj.sender_meta = (
                    sender_meta
                )

                message_obj.recipient_meta = (
                    recipient_meta
                )

                message_obj.subject = (
                    subject
                )

                message_obj.body = (
                    body
                )

                message_obj.attachment_meta = (
                    attachments
                )

                message_obj.received_at = (
                    received_at
                )

                message_obj.is_read = (
                    "UNREAD"
                    not in label_ids
                )

                message_obj.is_starred = (
                    "STARRED"
                    in label_ids
                )

                message_obj.is_draft = (
                    False
                )


                message_obj.save(
                    update_fields=[
                        "organization",
                        "email_account",
                        "conversation",
                        "platform",
                        "direction",
                        "folder",
                        "external_conversation_id",
                        "sender",
                        "recipients",
                        "sender_meta",
                        "recipient_meta",
                        "subject",
                        "body",
                        "attachment_meta",
                        "received_at",
                        "is_read",
                        "is_starred",
                        "is_draft",
                    ]
                )


                upgraded_count += 1


                log_event(
                    logger,
                    "info",
                    (
                        "gmail.message."
                        "upgraded_legacy"
                    ),
                    provider="gmail",
                    account_id=(
                        email_account.id
                    ),
                    message_id=(
                        message_obj.id
                    ),
                )


            else:

                message_obj = (
                    InboxMessage.objects.create(
                        user=user,
                        organization=(
                            organization
                        ),
                        email_account=(
                            email_account
                        ),
                        conversation=(
                            conversation
                        ),
                        platform="gmail",
                        direction=(
                            direction
                        ),
                        folder=folder,
                        external_message_id=(
                            provider_id
                        ),
                        external_conversation_id=(
                            thread_id
                        ),
                        sender=sender,
                        recipients=(
                            recipients
                        ),
                        sender_meta=(
                            sender_meta
                        ),
                        recipient_meta=(
                            recipient_meta
                        ),
                        subject=subject,
                        body=body,
                        attachment_meta=(
                            attachments
                        ),
                        received_at=(
                            received_at
                        ),
                        is_read=(
                            "UNREAD"
                            not in label_ids
                        ),
                        is_starred=(
                            "STARRED"
                            in label_ids
                        ),
                        is_draft=False,
                    )
                )


                created_count += 1


            _update_conversation_if_newer(
                conversation=(
                    conversation
                ),
                message=(
                    message_obj
                ),
            )


            invalidate_conversation_cache(
                user.id
            )


            try:

                MessageProcessor().process_message(
                    organization=(
                        organization
                    ),
                    message=(
                        message_obj
                    ),
                    sender=sender,
                    subject=subject,
                    body=body,
                    source_channel="gmail",
                )

                log_event(
                    logger,
                    "info",
                    "gmail.knowledge.processed",
                    provider="gmail",
                    account_id=(
                        email_account.id
                    ),
                )

            except Exception as exc:

                log_event(
                    logger,
                    "warning",
                    "gmail.knowledge.failed",
                    provider="gmail",
                    account_id=(
                        email_account.id
                    ),
                    error_type=(
                        type(exc).__name__
                    ),
                )


            # Do not flood a newly-connected browser with one
            # WebSocket event for every historical message.
            #
            # Incremental synchronization still emits live mail.
            if (
                not window.initial_history
            ):

                channel_layer = (
                    get_channel_layer()
                )


                async_to_sync(
                    channel_layer.group_send
                )(
                    f"inbox_{user.id}",
                    {
                        "type":
                            "inbox_update",

                        "data": {
                            "event":
                                "new_email",

                            "conversation_id":
                                conversation.id,

                            "subject":
                                subject,

                            "sender":
                                sender,

                            "preview":
                                body[:120],

                            "received_at":
                                received_at.isoformat(),

                            "platform":
                                "gmail",
                        },
                    },
                )


            log_event(
                logger,
                "info",
                "gmail.message.synced",
                provider="gmail",
                account_id=(
                    email_account.id
                ),
                conversation_id=(
                    conversation.id
                ),
                message_id=(
                    message_obj.id
                ),
            )


        except Exception as exc:

            failed_count += 1


            log_event(
                logger,
                "warning",
                "gmail.message.failed",
                provider="gmail",
                account_id=(
                    email_account.id
                ),
                failed_message_count=(
                    failed_count
                ),
                error_type=(
                    type(exc).__name__
                ),
            )


            continue


    if failed_count:

        raise RuntimeError(
            "Gmail partial sync failure: "
            f"{failed_count} message(s) failed."
        )


    if window.initial_history:

        mark_initial_history_complete(
            email_account=(
                email_account
            )
        )


    return {
        "initial_history":
            window.initial_history,

        "processed":
            processed_count,

        "created":
            created_count,

        "upgraded":
            upgraded_count,

        "skipped":
            skipped_count,

        "failed":
            failed_count,
    }


def fetch_gmail_emails(
    *,
    user,
    email_account,
    limit=None,
):
    update_sync_status(
        user=user,
        platform="gmail",
        status="syncing",
        progress=0,
        error_message="",
    )


    try:

        result = (
            _fetch_gmail_emails_impl(
                user=user,
                email_account=(
                    email_account
                ),
                limit=limit,
            )
        )

    except Exception as exc:

        update_sync_status(
            user=user,
            platform="gmail",
            status="failed",
            progress=0,
            error_message=(
                str(exc)
            ),
        )

        raise


    update_sync_status(
        user=user,
        platform="gmail",
        status="success",
        progress=100,
        error_message="",
    )


    return result
