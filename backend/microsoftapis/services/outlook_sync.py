from datetime import (
    timedelta,
    timezone as datetime_timezone,
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

import requests

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils.dateparse import parse_datetime

from inbox.models import (
    Conversation,
    InboxMessage,
)

from inbox.services.conversation_cache import (
    invalidate_conversation_cache,
)

from inbox.services.sync_status import (
    update_sync_status,
)

from inbox.services.mail_sync_policy import (
    OUTLOOK_PAGE_SIZE,
    mark_initial_history_complete,
    resolve_mail_sync_window,
)

from inbox.services.mail_mutations import (
    refresh_conversation_local_state,
)

from knowledge.services.message_processor import (
    MessageProcessor,
)

from microsoftapis.utils import (
    get_microsoft_access_token,
)

from platform_core.observability.logger import (
    get_logger,
    log_event,
)


logger = get_logger(
    "oneuch.runtime.outlook"
)


OUTLOOK_FOLDER_CONFIG = (
    {
        "graph_folder": "inbox",
        "local_folder": "inbox",
        "direction": "inbound",
        "timestamp_field": "receivedDateTime",
    },
    {
        "graph_folder": "sentitems",
        "local_folder": "sent",
        "direction": "outbound",
        "timestamp_field": "sentDateTime",
    },
)


def _graph_identity(
    value,
):
    email_data = (
        (value or {})
        .get(
            "emailAddress",
            {},
        )
        or {}
    )


    address = (
        str(
            email_data.get(
                "address",
                "",
            )
            or ""
        )
        .strip()
        .lower()
    )


    if not address:
        return {}


    return {
        "name":
            str(
                email_data.get(
                    "name",
                    "",
                )
                or ""
            ).strip(),

        "email":
            address,
    }


def _email_address(
    value,
):
    return (
        _graph_identity(
            value
        ).get(
            "email",
            ""
        )
    )


def _graph_identity_list(
    message,
    field,
):
    identities = []

    seen = set()


    for value in (
        message.get(
            field,
            [],
        )
        or []
    ):

        identity = (
            _graph_identity(
                value
            )
        )


        email_value = (
            identity.get(
                "email"
            )
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

        identities.append(
            identity
        )


    return identities


def _graph_recipient_meta(
    message,
):
    return {
        "to":
            _graph_identity_list(
                message,
                "toRecipients",
            ),

        "cc":
            _graph_identity_list(
                message,
                "ccRecipients",
            ),

        "bcc":
            _graph_identity_list(
                message,
                "bccRecipients",
            ),

        "reply_to":
            _graph_identity_list(
                message,
                "replyTo",
            ),
    }


def _graph_recipients(
    message,
):
    return [
        item["email"]
        for item in (
            _graph_recipient_meta(
                message
            )["to"]
        )
    ]


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


def _normalized_recipients(value):
    source = str(
        value or ""
    ).replace(
        ";",
        ",",
    )

    return {
        address.strip().lower()
        for _, address in getaddresses(
            [source]
        )
        if address
    }


def _candidate_to_recipient_set(
    candidate,
):
    """
    P2C reconciliation compares Graph To recipients with the
    local structured To bucket.

    The legacy flat recipients field may now contain
    To + CC + BCC, so it is only used as a fallback for older
    outbound rows that predate structured recipient metadata.
    """

    recipient_meta = (
        candidate.recipient_meta
        if isinstance(
            candidate.recipient_meta,
            dict,
        )
        else {}
    )


    structured_to = {
        str(
            item.get(
                "email",
                "",
            )
        )
        .strip()
        .lower()

        for item in (
            recipient_meta.get(
                "to",
                [],
            )
            or []
        )

        if (
            isinstance(
                item,
                dict,
            )
            and
            item.get(
                "email"
            )
        )
    }


    if structured_to:
        return structured_to


    return _normalized_recipients(
        candidate.recipients
    )


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


def _graph_body_text(
    message,
):
    body = (
        message.get(
            "body",
            {},
        )
        or {}
    )


    content = str(
        body.get(
            "content",
            "",
        )
        or ""
    )


    content_type = (
        str(
            body.get(
                "contentType",
                "text",
            )
            or "text"
        )
        .strip()
        .lower()
    )


    if content:

        if content_type == "html":

            return (
                _html_to_text(
                    content
                )
                .strip()
            )


        return content.strip()


    # Provider fallback only when Graph supplied no usable
    # full body. bodyPreview is never preferred over body.
    return (
        str(
            message.get(
                "bodyPreview",
                "",
            )
            or ""
        )
        .strip()
    )


def _extract_attachments(message):
    attachments = []

    if not message.get(
        "hasAttachments"
    ):
        return attachments

    for attachment in (
        message.get(
            "attachments",
            [],
        )
        or []
    ):
        if (
            attachment.get(
                "@odata.type"
            )
            !=
            "#microsoft.graph.fileAttachment"
        ):
            continue

        attachments.append(
            {
                "filename":
                    attachment.get(
                        "name"
                    ),

                "attachment_id":
                    attachment.get(
                        "id"
                    ),

                "mime_type":
                    attachment.get(
                        "contentType"
                    ),
            }
        )

    return attachments


def _message_timestamp(
    message,
    *,
    direction,
):
    if direction == "outbound":
        raw_value = (
            message.get(
                "sentDateTime"
            )
            or
            message.get(
                "receivedDateTime"
            )
        )
    else:
        raw_value = (
            message.get(
                "receivedDateTime"
            )
            or
            message.get(
                "sentDateTime"
            )
        )

    parsed = (
        parse_datetime(
            raw_value
        )
        if raw_value
        else None
    )

    if parsed is None:
        raise RuntimeError(
            "Microsoft Graph message "
            f"{message.get('id')} "
            "does not contain a valid timestamp."
        )

    return parsed


def _graph_cutoff_value(
    cutoff,
):
    if (
        cutoff.tzinfo
        is None
    ):
        aware = cutoff.replace(
            tzinfo=(
                datetime_timezone.utc
            )
        )

    else:

        aware = cutoff.astimezone(
            datetime_timezone.utc
        )


    return (
        aware
        .isoformat(
            timespec="seconds"
        )
        .replace(
            "+00:00",
            "Z",
        )
    )


def _fetch_folder(
    *,
    access_token,
    config,
    cutoff,
):
    graph_folder = (
        config[
            "graph_folder"
        ]
    )

    timestamp_field = (
        config[
            "timestamp_field"
        ]
    )


    base_url = (
        "https://graph.microsoft.com/"
        "v1.0/me/mailFolders/"
        f"{graph_folder}/messages"
    )


    headers = {
        "Authorization":
            f"Bearer {access_token}",

        # Ask Graph to materialize message.body as text.
        # _graph_body_text remains defensive if HTML is
        # returned despite the preference.
        "Prefer":
            'outlook.body-content-type="text"',
    }


    params = {
        "$top":
            OUTLOOK_PAGE_SIZE,

        "$filter":
            (
                f"{timestamp_field} ge "
                f"{_graph_cutoff_value(cutoff)}"
            ),

        "$select": (
            "id,"
            "subject,"
            "body,"
            "bodyPreview,"
            "conversationId,"
            "isRead,"
            "from,"
            "toRecipients,"
            "ccRecipients,"
            "bccRecipients,"
            "replyTo,"
            "receivedDateTime,"
            "sentDateTime,"
            "hasAttachments,"
            "flag"
        ),

        "$expand":
            "attachments",
    }


    messages = []

    next_url = None

    seen_next_links = set()

    page_index = 0


    while True:

        page_index += 1


        if next_url:

            response = requests.get(
                next_url,
                headers=headers,
            )

        else:

            response = requests.get(
                base_url,
                headers=headers,
                params=params,
            )


        log_event(
            logger,
            "info",
            "outlook.graph.response",
            provider="outlook",
            folder=graph_folder,
            page=page_index,
            status_code=(
                response.status_code
            ),
        )


        if response.status_code != 200:

            raise RuntimeError(
                "Microsoft Graph Outlook sync "
                f"failed for {graph_folder} "
                "with status "
                f"{response.status_code}."
            )


        payload = response.json()


        if not isinstance(
            payload,
            dict,
        ):

            raise RuntimeError(
                "Microsoft Graph Outlook sync "
                f"returned an invalid {graph_folder} "
                "response."
            )


        page_messages = (
            payload.get(
                "value",
                [],
            )
            or []
        )


        messages.extend(
            page_messages
        )


        candidate = (
            payload.get(
                "@odata.nextLink"
            )
        )


        if not candidate:
            break


        if candidate in seen_next_links:

            raise RuntimeError(
                "Microsoft Graph Outlook sync "
                f"repeated a pagination link for "
                f"{graph_folder}."
            )


        seen_next_links.add(
            candidate
        )

        next_url = candidate


    return messages

def _find_local_outbound_candidate(
    *,
    user,
    email_account,
    subject,
    recipients,
    body_preview,
    sent_at,
):
    """
    Reconcile a Graph Sent Item with a message that One UCH
    already persisted at send/reply time.

    Matching is intentionally conservative:
    - same account
    - outbound Outlook message
    - provider id not yet known (sent/pending)
    - sent status
    - exact subject
    - same normalized recipients
    - near the Graph sent timestamp
    - compatible body preview

    If zero or multiple candidates match, no reconciliation
    is attempted. This avoids attaching a provider message to
    the wrong local business record.
    """

    lower_bound = (
        sent_at
        - timedelta(
            minutes=10
        )
    )

    upper_bound = (
        sent_at
        + timedelta(
            minutes=10
        )
    )

    graph_recipient_set = {
        value.lower()
        for value in recipients
        if value
    }

    candidates = (
        InboxMessage.objects
        .filter(
            user=user,
            email_account=email_account,
            platform="outlook",
            direction="outbound",
            external_message_id__in=[
                "sent",
                "pending",
            ],
            status="sent",
            subject=subject,
            received_at__gte=(
                lower_bound
            ),
            received_at__lte=(
                upper_bound
            ),
        )
        .order_by(
            "id"
        )
    )

    matches = []

    normalized_preview = (
        body_preview
        or ""
    ).strip()

    for candidate in candidates:
        if (
            _candidate_to_recipient_set(
                candidate
            )
            != graph_recipient_set
        ):
            continue

        local_body = (
            candidate.body
            or ""
        ).strip()

        if (
            normalized_preview
            and local_body
            and not (
                local_body.startswith(
                    normalized_preview
                )
                or normalized_preview.startswith(
                    local_body
                )
            )
        ):
            continue

        matches.append(
            candidate
        )

    if len(matches) == 1:
        return matches[0]

    return None


def _resolve_conversation(
    *,
    user,
    organization,
    email_account,
    thread_id,
    subject,
    local_message=None,
):
    conversation_key = (
        f"outlook_{thread_id}"
    )

    provider_conversation = (
        Conversation.objects
        .filter(
            user=user,
            conversation_key=(
                conversation_key
            ),
        )
        .first()
    )

    local_conversation = (
        local_message.conversation
        if (
            local_message
            and
            local_message.conversation_id
        )
        else None
    )

    # Existing provider-native conversation wins.
    if provider_conversation:
        return provider_conversation

    # A locally-created compose/reply conversation can become
    # the provider-native conversation once Graph gives us the
    # real conversationId.
    if local_conversation:
        local_conversation.conversation_key = (
            conversation_key
        )

        local_conversation.external_conversation_id = (
            thread_id
        )

        local_conversation.email_account = (
            email_account
        )

        if (
            local_conversation.organization_id
            is None
        ):
            local_conversation.organization = (
                organization
            )

        local_conversation.save(
            update_fields=[
                "conversation_key",
                "external_conversation_id",
                "email_account",
                "organization",
            ]
        )

        return local_conversation

    return (
        Conversation.objects.create(
            user=user,
            organization=organization,
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
            email_account=(
                email_account
            ),
        )
    )


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

    conversation.save(
        update_fields=[
            "last_message",
            "last_message_at",
            "last_message_preview",
            "subject",
        ]
    )


def fetch_outlook_emails(
    *,
    user,
    email_account,
    limit=None,
):
    # `limit` remains accepted so older callers do not break.
    # P1B intentionally traverses the complete bounded window.
    del limit


    update_sync_status(
        user=user,
        platform="outlook",
        status="syncing",
        progress=0,
        error_message="",
    )


    window = (
        resolve_mail_sync_window(
            email_account=(
                email_account
            )
        )
    )


    latest_message = None

    processed_count = 0

    created_count = 0

    upgraded_count = 0

    skipped_count = 0

    reconciled_count = 0

    failed_count = 0


    try:

        access_token = (
            get_microsoft_access_token(
                user
            )
        )


        # Fetch every required provider page first.
        #
        # If Inbox/Sent provider completeness cannot be
        # established, no folder is persisted and the run
        # cannot falsely claim a complete mailbox.
        folder_batches = []


        for config in (
            OUTLOOK_FOLDER_CONFIG
        ):

            messages = (
                _fetch_folder(
                    access_token=(
                        access_token
                    ),
                    config=config,
                    cutoff=(
                        window.cutoff
                    ),
                )
            )


            folder_batches.append(
                (
                    config,
                    messages,
                )
            )


        organization = (
            user
            .organization_membership
            .organization
        )


        for (
            config,
            messages,
        ) in folder_batches:

            log_event(
                logger,
                "info",
                "outlook.folder.batch",
                provider="outlook",
                folder=(
                    config[
                        "graph_folder"
                    ]
                ),
                message_count=(
                    len(messages)
                ),
            )


            for graph_message in messages:

                try:

                    external_id = (
                        graph_message.get(
                            "id"
                        )
                    )


                    thread_id = (
                        graph_message.get(
                            "conversationId"
                        )
                    )


                    if (
                        not external_id
                        or
                        not thread_id
                    ):

                        raise RuntimeError(
                            "Microsoft Graph message "
                            "is missing id or "
                            "conversationId."
                        )


                    direction = (
                        config[
                            "direction"
                        ]
                    )


                    received_at = (
                        _message_timestamp(
                            graph_message,
                            direction=(
                                direction
                            ),
                        )
                    )


                    # Defence in depth: Graph receives an OData
                    # cutoff filter, but One UCH independently
                    # enforces the same boundary.
                    if (
                        received_at
                        <
                        window.cutoff
                    ):

                        continue


                    processed_count += 1


                    existing = (
                        InboxMessage.objects
                        .filter(
                            user=user,
                            external_message_id=(
                                external_id
                            ),
                            email_account=(
                                email_account
                            ),
                        )
                        .first()
                    )


                    if (
                        existing
                        and
                        not window.initial_history
                    ):

                        existing.folder = (
                            config[
                                "local_folder"
                            ]
                        )

                        existing.direction = (
                            direction
                        )

                        existing.external_conversation_id = (
                            thread_id
                        )

                        existing.is_read = (
                            graph_message.get(
                                "isRead",
                                (
                                    direction
                                    ==
                                    "outbound"
                                ),
                            )
                        )

                        existing.is_starred = (
                            (
                                graph_message.get(
                                    "flag",
                                    {},
                                )
                                or {}
                            ).get(
                                "flagStatus"
                            )
                            ==
                            "flagged"
                        )


                        existing.save(
                            update_fields=[
                                "folder",
                                "direction",
                                "external_conversation_id",
                                "is_read",
                                "is_starred",
                            ]
                        )


                        refresh_conversation_local_state(
                            existing.conversation
                        )


                        skipped_count += 1

                        continue


                    subject = (
                        graph_message.get(
                            "subject"
                        )
                        or "No Subject"
                    )


                    body_text = (
                        _graph_body_text(
                            graph_message
                        )
                    )


                    sender_meta = (
                        _graph_identity(
                            graph_message.get(
                                "from"
                            )
                        )
                    )


                    recipient_meta = (
                        _graph_recipient_meta(
                            graph_message
                        )
                    )


                    to_addresses = [
                        item["email"]
                        for item in (
                            recipient_meta[
                                "to"
                            ]
                        )
                    ]


                    sender = (
                        sender_meta.get(
                            "email",
                            "",
                        )
                    )


                    if (
                        direction
                        ==
                        "outbound"
                        and
                        not sender
                    ):

                        sender = (
                            email_account
                            .email_address
                            .strip()
                            .lower()
                        )


                        sender_meta = {
                            "name":
                                "",

                            "email":
                                sender,
                        }


                    recipients = (
                        _flatten_recipient_emails(
                            recipient_meta
                        )
                    )


                    if (
                        direction
                        ==
                        "inbound"
                        and
                        not recipients
                    ):

                        account_email = (
                            email_account
                            .email_address
                            .strip()
                            .lower()
                        )


                        recipient_meta[
                            "to"
                        ] = [
                            {
                                "name":
                                    "",

                                "email":
                                    account_email,
                            }
                        ]


                        recipients = (
                            account_email
                        )


                    local_candidate = None


                    if (
                        direction
                        ==
                        "outbound"
                    ):

                        local_candidate = (
                            _find_local_outbound_candidate(
                                user=user,
                                email_account=(
                                    email_account
                                ),
                                subject=subject,
                                recipients=(
                                    to_addresses
                                ),
                                body_preview=(
                                    body_text
                                ),
                                sent_at=(
                                    received_at
                                ),
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
                            local_message=(
                                existing
                                or
                                local_candidate
                            ),
                        )
                    )


                    if (
                        conversation
                        .email_account_id
                        is None
                    ):

                        conversation.email_account = (
                            email_account
                        )

                        conversation.save(
                            update_fields=[
                                "email_account",
                            ]
                        )


                    attachments = (
                        _extract_attachments(
                            graph_message
                        )
                    )


                    is_starred = (
                        (
                            graph_message.get(
                                "flag",
                                {},
                            )
                            or {}
                        ).get(
                            "flagStatus"
                        )
                        ==
                        "flagged"
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
                            "outlook"
                        )

                        message_obj.folder = (
                            config[
                                "local_folder"
                            ]
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
                            body_text
                        )

                        message_obj.attachment_meta = (
                            attachments
                        )

                        message_obj.received_at = (
                            received_at
                        )

                        message_obj.is_read = (
                            graph_message.get(
                                "isRead",
                                (
                                    direction
                                    ==
                                    "outbound"
                                ),
                            )
                        )

                        message_obj.is_starred = (
                            is_starred
                        )

                        message_obj.direction = (
                            direction
                        )

                        message_obj.is_draft = (
                            False
                        )


                        if (
                            direction
                            ==
                            "outbound"
                        ):

                            message_obj.status = (
                                "sent"
                            )


                        message_obj.save(
                            update_fields=[
                                "organization",
                                "email_account",
                                "conversation",
                                "platform",
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
                                "direction",
                                "is_draft",
                                "status",
                            ]
                        )


                        upgraded_count += 1


                        log_event(
                            logger,
                            "info",
                            (
                                "outlook.message."
                                "upgraded_legacy"
                            ),
                            provider="outlook",
                            account_id=(
                                email_account.id
                            ),
                            message_id=(
                                message_obj.id
                            ),
                        )


                    elif local_candidate:

                        message_obj = (
                            local_candidate
                        )


                        message_obj.conversation = (
                            conversation
                        )

                        message_obj.external_message_id = (
                            external_id
                        )

                        message_obj.external_conversation_id = (
                            thread_id
                        )

                        message_obj.folder = (
                            config[
                                "local_folder"
                            ]
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


                        # Keep the full local body created by
                        # One UCH when available. Otherwise use
                        # the provider's complete Graph body.
                        if not message_obj.body:

                            message_obj.body = (
                                body_text
                            )


                        message_obj.received_at = (
                            received_at
                        )

                        message_obj.is_read = True

                        message_obj.is_starred = (
                            is_starred
                        )

                        message_obj.direction = (
                            "outbound"
                        )

                        message_obj.is_draft = False

                        message_obj.status = (
                            "sent"
                        )


                        if attachments:

                            message_obj.attachment_meta = (
                                attachments
                            )


                        message_obj.save(
                            update_fields=[
                                "conversation",
                                "external_message_id",
                                "external_conversation_id",
                                "folder",
                                "sender",
                                "recipients",
                                "sender_meta",
                                "recipient_meta",
                                "subject",
                                "body",
                                "received_at",
                                "is_read",
                                "is_starred",
                                "direction",
                                "is_draft",
                                "status",
                                "attachment_meta",
                            ]
                        )


                        reconciled_count += 1


                    else:

                        message_obj = (
                            InboxMessage.objects.create(
                                user=user,
                                organization=(
                                    organization
                                ),
                                conversation=(
                                    conversation
                                ),
                                platform="outlook",
                                folder=(
                                    config[
                                        "local_folder"
                                    ]
                                ),
                                external_message_id=(
                                    external_id
                                ),
                                external_conversation_id=(
                                    thread_id
                                ),
                                sender=(
                                    sender
                                ),
                                recipients=(
                                    recipients
                                ),
                                sender_meta=(
                                    sender_meta
                                ),
                                recipient_meta=(
                                    recipient_meta
                                ),
                                subject=(
                                    subject
                                ),
                                attachment_meta=(
                                    attachments
                                ),
                                body=(
                                    body_text
                                ),
                                received_at=(
                                    received_at
                                ),
                                is_read=(
                                    graph_message.get(
                                        "isRead",
                                        (
                                            direction
                                            ==
                                            "outbound"
                                        ),
                                    )
                                ),
                                is_starred=(
                                    is_starred
                                ),
                                direction=(
                                    direction
                                ),
                                is_draft=False,
                                email_account=(
                                    email_account
                                ),
                            )
                        )


                        created_count += 1


                    try:

                        processor = (
                            MessageProcessor()
                        )


                        processor.process_message(
                            organization=(
                                organization
                            ),
                            message=(
                                message_obj
                            ),
                            sender=(
                                message_obj
                                .sender
                            ),
                            subject=(
                                message_obj
                                .subject
                            ),
                            body=(
                                message_obj
                                .body
                            ),
                            source_channel=(
                                "outlook"
                            ),
                        )


                    except Exception as exc:

                        log_event(
                            logger,
                            "warning",
                            "outlook.knowledge.failed",
                            provider="outlook",
                            message_id=(
                                message_obj.id
                            ),
                            error_type=(
                                type(exc).__name__
                            ),
                        )


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


                    if (
                        latest_message
                        is None
                        or
                        message_obj.received_at
                        >
                        latest_message.received_at
                    ):

                        latest_message = (
                            message_obj
                        )


                except Exception as exc:

                    failed_count += 1


                    log_event(
                        logger,
                        "warning",
                        "outlook.message.failed",
                        provider="outlook",
                        folder=(
                            config[
                                "graph_folder"
                            ]
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
                "Outlook partial sync failure: "
                f"{failed_count} message(s) failed."
            )


        if window.initial_history:

            mark_initial_history_complete(
                email_account=(
                    email_account
                )
            )


    except Exception as exc:

        update_sync_status(
            user=user,
            platform="outlook",
            status="failed",
            progress=0,
            error_message=(
                str(exc)
            ),
        )


        log_event(
            logger,
            "error",
            "outlook.sync.failed",
            provider="outlook",
            account_id=(
                email_account.id
            ),
            error_type=(
                type(exc).__name__
            ),
        )


        raise


    update_sync_status(
        user=user,
        platform="outlook",
        status="success",
        progress=100,
        error_message="",
    )


    # Historical backfill can contain thousands of messages.
    # Do not flood the connected browser with one provider
    # notification per historical import.
    if (
        latest_message
        and
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
                        (
                            latest_message
                            .conversation_id
                        ),

                    "subject":
                        latest_message.subject,

                    "sender":
                        latest_message.sender,

                    "preview":
                        (
                            latest_message
                            .body[:120]
                        ),

                    "received_at":
                        (
                            latest_message
                            .received_at
                            .isoformat()
                        ),

                    "platform":
                        "outlook",
                },
            },
        )


    log_event(
        logger,
        "info",
        "outlook.sync.completed",
        provider="outlook",
        account_id=(
            email_account.id
        ),
        folder_count=(
            len(
                OUTLOOK_FOLDER_CONFIG
            )
        ),
        processed_count=(
            processed_count
        ),
        created_count=(
            created_count
        ),
        upgraded_count=(
            upgraded_count
        ),
        skipped_count=(
            skipped_count
        ),
        reconciled_count=(
            reconciled_count
        ),
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

        "reconciled":
            reconciled_count,

        "failed":
            failed_count,
    }
