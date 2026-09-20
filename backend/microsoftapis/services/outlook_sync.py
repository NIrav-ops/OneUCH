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


OUTLOOK_DELETED_DELTA_STATE_KEY = (
    "_outlook_deleted_items_delta_link"
)

OUTLOOK_DELETED_PAGE_SIZE = 100

OUTLOOK_TRANSLATE_BATCH_SIZE = 1000


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

def _deleted_delta_link(
    email_account,
):
    state = (
        email_account.last_synced_uids
        if isinstance(
            email_account.last_synced_uids,
            dict,
        )
        else {}
    )

    return str(
        state.get(
            OUTLOOK_DELETED_DELTA_STATE_KEY,
            "",
        )
        or ""
    ).strip()


def _save_deleted_delta_link(
    *,
    email_account,
    delta_link,
):
    value = str(
        delta_link
        or ""
    ).strip()

    if not value:
        raise RuntimeError(
            "Microsoft Graph Deleted Items delta "
            "did not return a delta link."
        )

    state = (
        dict(
            email_account.last_synced_uids
        )
        if isinstance(
            email_account.last_synced_uids,
            dict,
        )
        else {}
    )

    state[
        OUTLOOK_DELETED_DELTA_STATE_KEY
    ] = value

    email_account.last_synced_uids = (
        state
    )

    email_account.save(
        update_fields=[
            "last_synced_uids",
        ]
    )


def _fetch_deleted_item_delta(
    *,
    access_token,
    email_account,
):
    saved_delta_link = (
        _deleted_delta_link(
            email_account
        )
    )

    url = (
        saved_delta_link
        or
        (
            "https://graph.microsoft.com/"
            "v1.0/me/mailFolders/"
            "deleteditems/messages/delta"
        )
    )

    headers = {
        "Authorization":
            f"Bearer {access_token}",

        "Prefer":
            (
                'IdType="ImmutableId", '
                f"odata.maxpagesize={OUTLOOK_DELETED_PAGE_SIZE}"
            ),
    }

    params = (
        None
        if saved_delta_link
        else {
            "$select":
                "id",
        }
    )

    changed_ids = set()

    change_count = 0

    page_index = 0

    seen_next_links = set()

    final_delta_link = None


    while url:

        page_index += 1

        response = requests.get(
            url,
            headers=headers,
            params=(
                params
                if page_index == 1
                else None
            ),
            timeout=30,
        )

        log_event(
            logger,
            "info",
            "outlook.deleted.delta.response",
            provider="outlook",
            account_id=(
                email_account.id
            ),
            page=page_index,
            status_code=(
                response.status_code
            ),
            incremental=bool(
                saved_delta_link
            ),
        )

        if response.status_code != 200:
            raise RuntimeError(
                "Microsoft Graph Deleted Items delta "
                "failed with status "
                f"{response.status_code}."
            )

        payload = response.json()

        if not isinstance(
            payload,
            dict,
        ):
            raise RuntimeError(
                "Microsoft Graph Deleted Items delta "
                "returned an invalid response."
            )

        values = (
            payload.get(
                "value",
                [],
            )
            or []
        )

        change_count += len(
            values
        )

        for item in values:

            if not isinstance(
                item,
                dict,
            ):
                continue

            # @removed means an item left Deleted Items
            # (restore/permanent deletion). That is not an
            # inbound trash event and is deliberately ignored.
            if item.get(
                "@removed"
            ):
                continue

            immutable_id = str(
                item.get(
                    "id"
                )
                or ""
            ).strip()

            if immutable_id:
                changed_ids.add(
                    immutable_id
                )

        next_link = str(
            payload.get(
                "@odata.nextLink"
            )
            or ""
        ).strip()

        if next_link:

            if next_link in seen_next_links:
                raise RuntimeError(
                    "Microsoft Graph Deleted Items delta "
                    "repeated a pagination link."
                )

            seen_next_links.add(
                next_link
            )

            url = next_link
            params = None
            continue

        final_delta_link = str(
            payload.get(
                "@odata.deltaLink"
            )
            or ""
        ).strip()

        url = None


    if not final_delta_link:
        raise RuntimeError(
            "Microsoft Graph Deleted Items delta "
            "did not return a delta link."
        )


    return {
        "changed_ids":
            changed_ids,

        "change_count":
            change_count,

        "delta_link":
            final_delta_link,

        "initial_delta":
            not bool(
                saved_delta_link
            ),
    }


def _translate_rest_ids_to_immutable(
    *,
    access_token,
    source_ids,
):
    normalized_ids = []

    seen = set()


    for value in source_ids:

        source_id = str(
            value
            or ""
        ).strip()

        if (
            not source_id
            or
            source_id in seen
        ):
            continue

        seen.add(
            source_id
        )

        normalized_ids.append(
            source_id
        )


    translated = {}


    for start in range(
        0,
        len(normalized_ids),
        OUTLOOK_TRANSLATE_BATCH_SIZE,
    ):

        batch = normalized_ids[
            start:
            start
            +
            OUTLOOK_TRANSLATE_BATCH_SIZE
        ]

        response = requests.post(
            (
                "https://graph.microsoft.com/"
                "v1.0/me/translateExchangeIds"
            ),
            headers={
                "Authorization":
                    f"Bearer {access_token}",

                "Content-Type":
                    "application/json",
            },
            json={
                "inputIds":
                    batch,

                "sourceIdType":
                    "restId",

                "targetIdType":
                    "restImmutableEntryId",
            },
            timeout=30,
        )

        if response.status_code != 200:
            raise RuntimeError(
                "Microsoft Graph ID translation "
                "failed with status "
                f"{response.status_code}."
            )

        payload = response.json()

        if not isinstance(
            payload,
            dict,
        ):
            raise RuntimeError(
                "Microsoft Graph ID translation "
                "returned an invalid response."
            )


        for item in (
            payload.get(
                "value",
                [],
            )
            or []
        ):

            if not isinstance(
                item,
                dict,
            ):
                continue

            source_id = str(
                item.get(
                    "sourceId"
                )
                or ""
            ).strip()

            target_id = str(
                item.get(
                    "targetId"
                )
                or ""
            ).strip()

            if (
                source_id
                and
                target_id
            ):
                translated[
                    source_id
                ] = target_id


    return translated


def _reconcile_deleted_items(
    *,
    user,
    email_account,
    access_token,
):
    delta = (
        _fetch_deleted_item_delta(
            access_token=(
                access_token
            ),
            email_account=(
                email_account
            ),
        )
    )

    changed_ids = (
        delta[
            "changed_ids"
        ]
    )

    reconciled = 0

    touched_conversations = set()


    if changed_ids:

        messages = (
            InboxMessage.objects
            .filter(
                user=user,
                email_account=(
                    email_account
                ),
                platform="outlook",
                is_draft=False,
                outlook_immutable_id__in=(
                    changed_ids
                ),
            )
            .exclude(
                folder="trash"
            )
            .select_related(
                "conversation"
            )
            .order_by(
                "id"
            )
        )


        for message in messages:

            message.folder = (
                "trash"
            )

            message.save(
                update_fields=[
                    "folder",
                ]
            )

            if (
                message.conversation_id
            ):
                touched_conversations.add(
                    message.conversation_id
                )

                refresh_conversation_local_state(
                    message.conversation
                )

            reconciled += 1


        if reconciled:
            invalidate_conversation_cache(
                user.id
            )


    # Cursor advances only after local reconciliation has
    # completed successfully.
    _save_deleted_delta_link(
        email_account=(
            email_account
        ),
        delta_link=(
            delta[
                "delta_link"
            ]
        ),
    )


    log_event(
        logger,
        "info",
        "outlook.deleted.delta.completed",
        provider="outlook",
        account_id=(
            email_account.id
        ),
        provider_change_count=(
            delta[
                "change_count"
            ]
        ),
        reconciled_count=(
            reconciled
        ),
        initial_delta=(
            delta[
                "initial_delta"
            ]
        ),
    )


    return {
        "changes":
            delta[
                "change_count"
            ],

        "reconciled":
            reconciled,

        "conversation_ids":
            touched_conversations,
    }


def _normalized_reconciliation_text(
    value,
):
    return (
        " ".join(
            str(
                value
                or ""
            )
            .split()
        )
        .casefold()
    )


def _find_local_outbound_candidate(
    *,
    user,
    email_account,
    subject,
    recipients,
    body_preview,
    sent_at,
    thread_id=None,
):
    """
    Conservatively reconcile a Graph Sent Item with a One UCH
    outbound placeholder.

    Native Microsoft Reply / Reply-All can normalize:
    - subject casing (Re: / RE:)
    - whitespace and line breaks in the reply body
    - quoted body formatting.

    Graph conversationId is therefore the strongest available
    stable identity for a native reply.

    Rules:
    - same user/account
    - Outlook outbound
    - unresolved provider id only (sent/pending)
    - sent state
    - within ten minutes of provider Sent time
    - same Graph conversation when both sides have one
    - normalized subject equality
    - same normalized To recipients

    If exactly one candidate survives those strong constraints,
    it is safe to reconcile.

    If more than one survives (for example, two replies in the
    same thread within ten minutes), normalized body text is used
    only as a secondary discriminator.

    Zero or ambiguous matches are intentionally not reconciled.
    """
    lower_bound = (
        sent_at
        -
        timedelta(
            minutes=10
        )
    )


    upper_bound = (
        sent_at
        +
        timedelta(
            minutes=10
        )
    )


    graph_recipient_set = {
        str(
            value
        )
        .strip()
        .lower()

        for value
        in recipients

        if str(
            value
            or ""
        ).strip()
    }


    normalized_subject = (
        _normalized_reconciliation_text(
            subject
        )
    )


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


    strong_matches = []


    for candidate in candidates:

        candidate_thread = (
            str(
                candidate.external_conversation_id
                or ""
            )
            .strip()
        )


        provider_thread = (
            str(
                thread_id
                or ""
            )
            .strip()
        )


        if (
            provider_thread
            and
            candidate_thread
            and
            provider_thread
            !=
            candidate_thread
        ):
            continue


        if (
            _normalized_reconciliation_text(
                candidate.subject
            )
            !=
            normalized_subject
        ):
            continue


        if (
            _candidate_to_recipient_set(
                candidate
            )
            !=
            graph_recipient_set
        ):
            continue


        strong_matches.append(
            candidate
        )


    if len(
        strong_matches
    ) == 1:

        return (
            strong_matches[0]
        )


    if len(
        strong_matches
    ) != 0:

        normalized_preview = (
            _normalized_reconciliation_text(
                body_preview
            )
        )


        body_matches = []


        for candidate in strong_matches:

            normalized_local_body = (
                _normalized_reconciliation_text(
                    candidate.body
                )
            )


            if (
                not normalized_preview
                or
                not normalized_local_body
            ):

                continue


            if (
                normalized_local_body.startswith(
                    normalized_preview
                )
                or
                normalized_preview.startswith(
                    normalized_local_body
                )
            ):

                body_matches.append(
                    candidate
                )


        if len(
            body_matches
        ) == 1:

            return (
                body_matches[0]
            )


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

    trash_change_count = 0

    trash_reconciled_count = 0

    trash_reconcile_failed = False

    immutable_identity_failed = False

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


            source_ids = [
                message.get(
                    "id"
                )
                for message in messages
                if message.get(
                    "id"
                )
            ]


            immutable_ids = {}


            try:

                immutable_ids = (
                    _translate_rest_ids_to_immutable(
                        access_token=(
                            access_token
                        ),
                        source_ids=(
                            source_ids
                        ),
                    )
                )


                if (
                    len(
                        immutable_ids
                    )
                    !=
                    len(
                        set(
                            source_ids
                        )
                    )
                ):

                    immutable_identity_failed = (
                        True
                    )

                    log_event(
                        logger,
                        "warning",
                        (
                            "outlook.immutable_identity."
                            "incomplete"
                        ),
                        provider="outlook",
                        account_id=(
                            email_account.id
                        ),
                        expected_count=(
                            len(
                                set(
                                    source_ids
                                )
                            )
                        ),
                        translated_count=(
                            len(
                                immutable_ids
                            )
                        ),
                    )


            except Exception as exc:

                immutable_identity_failed = (
                    True
                )

                immutable_ids = {}

                log_event(
                    logger,
                    "warning",
                    "outlook.immutable_identity.failed",
                    provider="outlook",
                    account_id=(
                        email_account.id
                    ),
                    error_type=(
                        type(exc).__name__
                    ),
                )


            folder_batches.append(
                (
                    config,
                    messages,
                    immutable_ids,
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
            immutable_ids,
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


                    immutable_id = str(
                        immutable_ids.get(
                            str(
                                external_id
                            ).strip(),
                            "",
                        )
                        or ""
                    ).strip()


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


                        if (
                            immutable_id
                            and
                            existing.outlook_immutable_id
                            !=
                            immutable_id
                        ):

                            existing.outlook_immutable_id = (
                                immutable_id
                            )

                            existing.save(
                                update_fields=[
                                    "outlook_immutable_id",
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
                                thread_id=(
                                    thread_id
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


                    if (
                        immutable_id
                        and
                        message_obj.outlook_immutable_id
                        !=
                        immutable_id
                    ):

                        message_obj.outlook_immutable_id = (
                            immutable_id
                        )

                        message_obj.save(
                            update_fields=[
                                "outlook_immutable_id",
                            ]
                        )


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


        if immutable_identity_failed:

            trash_reconcile_failed = True

            log_event(
                logger,
                "warning",
                "outlook.deleted.delta.deferred_identity",
                provider="outlook",
                account_id=(
                    email_account.id
                ),
            )


        else:

            try:

                trash_result = (
                    _reconcile_deleted_items(
                        user=user,
                        email_account=(
                            email_account
                        ),
                        access_token=(
                            access_token
                        ),
                    )
                )

                trash_change_count = (
                    trash_result[
                        "changes"
                    ]
                )

                trash_reconciled_count = (
                    trash_result[
                        "reconciled"
                    ]
                )

            except Exception as exc:

                trash_reconcile_failed = True

                log_event(
                    logger,
                    "warning",
                    "outlook.deleted.delta.failed",
                    provider="outlook",
                    account_id=(
                        email_account.id
                    ),
                    error_type=(
                        type(exc).__name__
                    ),
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


    if (
        trash_reconciled_count
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
                        "mailbox_changed",

                    "reason":
                        "trash_reconciled",

                    "platform":
                        "outlook",

                    "reconciled":
                        trash_reconciled_count,
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
        trash_change_count=(
            trash_change_count
        ),
        trash_reconciled_count=(
            trash_reconciled_count
        ),
        trash_reconcile_failed=(
            trash_reconcile_failed
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

        "trash_changes":
            trash_change_count,

        "trash_reconciled":
            trash_reconciled_count,

        "trash_reconcile_failed":
            trash_reconcile_failed,

        "failed":
            failed_count,
    }
