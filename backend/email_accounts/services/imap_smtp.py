import hashlib
import imaplib
import email
import re

from datetime import (
    datetime,
    timezone as datetime_timezone,
)

from email.header import (
    decode_header,
    make_header,
)

from email.utils import (
    getaddresses,
    parsedate_to_datetime,
)

from html import (
    unescape,
)

from html.parser import (
    HTMLParser,
)

from django.utils import timezone

from email_accounts.services.mailbox_network_policy import (
    connect_validated_mailbox_endpoint,
    create_verified_tls_context,
    validate_mailbox_endpoint,
)

from inbox.models import (
    Conversation,
    InboxMessage,
)

from inbox.services.conversation_cache import (
    invalidate_conversation_cache,
)

from inbox.services.mail_mutations import (
    refresh_conversation_local_state,
)

from inbox.services.mail_sync_policy import (
    mark_initial_history_complete,
    resolve_mail_sync_window,
)

from inbox.services.sync_status import (
    update_sync_status,
)

from inbox.notifications.services import (
    create_notification,
)

from knowledge.services.message_processor import (
    MessageProcessor,
)

from platform_core.observability.logger import (
    get_logger,
    log_event,
)

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


logger = get_logger(
    "oneuch.runtime.imap"
)


class _PinnedIMAP4SSL(
    imaplib.IMAP4_SSL
):
    """
    IMAP TLS client whose TCP connection is pinned to the
    already-policy-validated address set while TLS hostname
    verification continues to use the configured hostname.
    """

    def __init__(
        self,
        endpoint,
        *,
        timeout=None,
    ):
        self._validated_endpoint = (
            endpoint
        )

        super().__init__(
            endpoint.host,
            endpoint.port,
            ssl_context=(
                create_verified_tls_context()
            ),
            timeout=timeout,
        )

    def _create_socket(
        self,
        timeout,
    ):
        raw_socket = (
            connect_validated_mailbox_endpoint(
                endpoint=(
                    self._validated_endpoint
                ),
                timeout=timeout,
            )
        )

        try:
            return (
                self.ssl_context
                .wrap_socket(
                    raw_socket,
                    server_hostname=(
                        self.host
                    ),
                )
            )

        except Exception:
            raw_socket.close()
            raise



# ================================
# IMAP INGESTION NORMALIZATION
# ================================


IMAP_SENT_ALIASES = (
    "sent",
    "sent items",
    "sent mail",
    "sent messages",
)


IMAP_LIST_PATTERN = re.compile(
    r'^'
    r'\((?P<flags>[^)]*)\)'
    r'\s+'
    r'(?P<delimiter>NIL|"(?:\\.|[^"])*")'
    r'\s+'
    r'(?P<name>.+)'
    r'$',
    re.IGNORECASE,
)


INTERNALDATE_PATTERN = re.compile(
    r'INTERNALDATE\s+"([^"]+)"',
    re.IGNORECASE,
)


MESSAGE_ID_PATTERN = re.compile(
    r'<[^<>\s]+>'
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
        value = (
            str(
                data
                or ""
            )
            .strip()
        )

        if value:

            self.parts.append(
                value
            )


    def text(
        self,
    ):
        return (
            "\n"
            .join(
                self.parts
            )
            .strip()
        )


def _decode_header_value(
    value,
):
    source = str(
        value
        or ""
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
    message,
    name,
):
    return [
        _decode_header_value(
            value
        )
        for value in (
            message.get_all(
                name,
                []
            )
            or []
        )
    ]


def _normalize_addresses(
    values,
):
    addresses = []

    seen = set()


    for (
        display_name,
        address,
    ) in getaddresses(
        [
            str(value)
            for value in (
                values
                or []
            )
            if value
        ]
    ):

        email_value = (
            str(
                address
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


def _message_identities(
    message,
):
    sender_candidates = (
        _normalize_addresses(
            _header_values(
                message,
                "From",
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
                    message,
                    "To",
                )
            ),

        "cc":
            _normalize_addresses(
                _header_values(
                    message,
                    "Cc",
                )
            ),

        "bcc":
            _normalize_addresses(
                _header_values(
                    message,
                    "Bcc",
                )
            ),

        "reply_to":
            _normalize_addresses(
                _header_values(
                    message,
                    "Reply-To",
                )
            ),
    }


    return (
        sender_meta,
        recipient_meta,
    )


def _flatten_recipient_emails(
    recipient_meta,
):
    values = []

    seen = set()


    for bucket in (
        "to",
        "cc",
        "bcc",
    ):

        for item in (
            recipient_meta.get(
                bucket,
                [],
            )
            or []
        ):

            if not isinstance(
                item,
                dict,
            ):
                continue

            value = (
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
                not value
                or
                value in seen
            ):
                continue

            seen.add(
                value
            )

            values.append(
                value
            )


    return ", ".join(
        values
    )


def _decode_payload(
    part,
):
    payload = (
        part.get_payload(
            decode=True
        )
    )

    if payload is None:

        return ""

    charset = (
        part.get_content_charset()
        or
        "utf-8"
    )

    try:

        return (
            payload
            .decode(
                charset
            )
            .strip()
        )

    except (
        LookupError,
        UnicodeDecodeError,
    ):

        return (
            payload
            .decode(
                "utf-8",
                errors="replace",
            )
            .strip()
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
                value
                or ""
            )
        )

        parser.close()

        return unescape(
            parser.text()
        )

    except Exception:

        return unescape(
            str(
                value
                or ""
            )
        )


def _extract_imap_body(
    message,
):
    plain_parts = []

    html_parts = []


    for part in (
        message.walk()
        if message.is_multipart()
        else [message]
    ):

        if part.is_multipart():

            continue

        disposition = (
            str(
                part.get_content_disposition()
                or ""
            )
            .lower()
        )

        if disposition == "attachment":

            continue

        content_type = (
            str(
                part.get_content_type()
                or ""
            )
            .lower()
        )

        if content_type not in {
            "text/plain",
            "text/html",
        }:

            continue

        value = (
            _decode_payload(
                part
            )
        )

        if not value:

            continue

        if content_type == "text/plain":

            plain_parts.append(
                value
            )

        else:

            html_parts.append(
                value
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
            for value in (
                html_parts
            )
        ).strip()


    return ""


def _extract_imap_attachments(
    message,
):
    attachments = []


    for part in (
        message.walk()
        if message.is_multipart()
        else [message]
    ):

        filename = (
            part.get_filename()
        )

        if not filename:

            continue

        attachments.append(
            {
                "filename":
                    _decode_header_value(
                        filename
                    ),

                "attachment_id":
                    None,

                "mime_type":
                    part.get_content_type(),
            }
        )


    return attachments


def _parse_internaldate(
    metadata,
):
    source = str(
        metadata
        or ""
    )

    match = (
        INTERNALDATE_PATTERN.search(
            source
        )
    )

    if match is None:

        return None

    try:

        return datetime.strptime(
            match.group(1),
            "%d-%b-%Y %H:%M:%S %z",
        )

    except ValueError:

        return None


def _message_timestamp(
    message,
    fetch_metadata,
):
    raw_date = (
        _decode_header_value(
            message.get(
                "Date",
                "",
            )
        )
        .strip()
    )

    if raw_date:

        try:

            parsed = (
                parsedate_to_datetime(
                    raw_date
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            parsed = None


        if parsed is not None:

            if parsed.tzinfo is None:

                parsed = (
                    parsed.replace(
                        tzinfo=(
                            datetime_timezone.utc
                        )
                    )
                )

            return parsed


    internal_date = (
        _parse_internaldate(
            fetch_metadata
        )
    )

    if internal_date is not None:

        return internal_date


    raise RuntimeError(
        "IMAP message does not contain "
        "a valid source timestamp."
    )


def _message_id_tokens(
    value,
):
    source = str(
        value
        or ""
    ).strip()

    if not source:

        return []

    matches = (
        MESSAGE_ID_PATTERN.findall(
            source
        )
    )

    if matches:

        return matches


    return [
        item.strip()
        for item in (
            source.split()
        )
        if item.strip()
    ]


def _first_message_id(
    value,
):
    values = (
        _message_id_tokens(
            value
        )
    )

    return (
        values[0]
        if values
        else ""
    )


def _thread_identity(
    message,
    *,
    fallback,
):
    references = (
        _message_id_tokens(
            message.get(
                "References"
            )
        )
    )

    if references:

        return references[0]


    in_reply_to = (
        _first_message_id(
            message.get(
                "In-Reply-To"
            )
        )
    )

    if in_reply_to:

        return in_reply_to


    message_id = (
        _first_message_id(
            message.get(
                "Message-ID"
            )
        )
    )

    if message_id:

        return message_id


    return fallback


def _bounded_identity(
    value,
):
    source = str(
        value
        or ""
    ).strip()

    if not source:

        return ""

    if len(source) <= 255:

        return source


    return (
        "sha256:"
        + hashlib.sha256(
            source.encode(
                "utf-8"
            )
        )
        .hexdigest()
    )


def _stable_external_message_id(
    *,
    email_account,
    folder_key,
    uid,
    uidvalidity,
    message,
):
    message_id = (
        _first_message_id(
            message.get(
                "Message-ID"
            )
        )
    )

    if message_id:

        identity = (
            message_id
            .strip()
            .casefold()
        )

        return (
            "imap-rfc822-"
            + hashlib.sha256(
                identity.encode(
                    "utf-8"
                )
            )
            .hexdigest()
        )


    fallback = (
        str(
            email_account.id
        )
        + "|"
        + str(
            folder_key
        )
        + "|"
        + str(
            uidvalidity
            or "unknown"
        )
        + "|"
        + str(
            uid
        )
    )


    return (
        "imap-uid-"
        + hashlib.sha256(
            fallback.encode(
                "utf-8"
            )
        )
        .hexdigest()
    )


def _unquote_imap_token(
    value,
):
    source = str(
        value
        or ""
    ).strip()

    if (
        len(source) >= 2
        and
        source.startswith('"')
        and
        source.endswith('"')
    ):

        source = (
            source[
                1:-1
            ]
            .replace(
                r'\"',
                '"',
            )
            .replace(
                r'\\',
                '\\',
            )
        )


    return source


def _parse_imap_list_entry(
    value,
):
    if isinstance(
        value,
        bytes,
    ):

        source = (
            value.decode(
                "utf-8",
                errors="replace",
            )
        )

    else:

        source = str(
            value
            or ""
        )


    source = source.strip()

    match = (
        IMAP_LIST_PATTERN.match(
            source
        )
    )

    if match is None:

        return None


    flags = {
        item.casefold()
        for item in (
            match.group(
                "flags"
            )
            .split()
        )
        if item
    }


    raw_delimiter = (
        match.group(
            "delimiter"
        )
    )


    delimiter = (
        None
        if (
            raw_delimiter
            .upper()
            ==
            "NIL"
        )
        else
        _unquote_imap_token(
            raw_delimiter
        )
    )


    name = (
        _unquote_imap_token(
            match.group(
                "name"
            )
        )
    )


    return {
        "flags":
            flags,

        "delimiter":
            delimiter,

        "name":
            name,
    }


def _mailbox_leaf(
    entry,
):
    name = (
        entry[
            "name"
        ]
    )

    delimiter = (
        entry.get(
            "delimiter"
        )
    )

    if (
        delimiter
        and
        delimiter in name
    ):

        name = (
            name
            .rsplit(
                delimiter,
                1,
            )[-1]
        )


    return (
        name.strip()
        .casefold()
    )


def _discover_imap_folders(
    folder_list,
):
    entries = []


    for raw in (
        folder_list
        or []
    ):

        entry = (
            _parse_imap_list_entry(
                raw
            )
        )

        if entry is not None:

            entries.append(
                entry
            )


    special_sent = [
        entry
        for entry in entries
        if (
            r"\sent"
            in
            entry[
                "flags"
            ]
        )
    ]


    if len(
        special_sent
    ) > 1:

        raise RuntimeError(
            "IMAP Sent folder discovery is ambiguous."
        )


    if special_sent:

        sent_name = (
            special_sent[0][
                "name"
            ]
        )

    else:

        sent_name = None


        for alias in (
            IMAP_SENT_ALIASES
        ):

            matches = [
                entry
                for entry in entries
                if (
                    _mailbox_leaf(
                        entry
                    )
                    ==
                    alias
                )
            ]


            if len(
                matches
            ) > 1:

                raise RuntimeError(
                    "IMAP Sent folder discovery is ambiguous."
                )


            if matches:

                sent_name = (
                    matches[0][
                        "name"
                    ]
                )

                break


    if not sent_name:

        raise RuntimeError(
            "Unable to discover IMAP Sent folder."
        )


    return (
        {
            "folder_key":
                "inbox",

            "folder_name":
                "INBOX",

            "direction":
                "inbound",
        },

        {
            "folder_key":
                "sent",

            "folder_name":
                sent_name,

            "direction":
                "outbound",
        },
    )


def _quote_imap_mailbox(
    value,
):
    source = str(
        value
        or ""
    )

    source = (
        source
        .replace(
            "\\",
            "\\\\",
        )
        .replace(
            '"',
            '\\"',
        )
    )

    return (
        '"'
        + source
        + '"'
    )


def _current_uidvalidity(
    mail,
):
    try:

        _, values = (
            mail.response(
                "UIDVALIDITY"
            )
        )

    except Exception:

        return None


    for value in (
        values
        or []
    ):

        if isinstance(
            value,
            bytes,
        ):

            source = (
                value.decode(
                    "ascii",
                    errors="ignore",
                )
            )

        else:

            source = str(
                value
                or ""
            )


        match = re.search(
            r"\d+",
            source,
        )

        if match:

            return match.group(0)


    return None


def _folder_last_uid(
    state,
    *,
    folder_key,
    uidvalidity,
):
    if not isinstance(
        state,
        dict,
    ):

        return 0


    validity_state = (
        state.get(
            "_uidvalidity",
            {},
        )
    )

    if not isinstance(
        validity_state,
        dict,
    ):

        validity_state = {}


    previous_validity = (
        validity_state.get(
            folder_key
        )
    )


    if (
        previous_validity
        and
        uidvalidity
        and
        str(
            previous_validity
        )
        !=
        str(
            uidvalidity
        )
    ):

        return 0


    try:

        return max(
            0,
            int(
                state.get(
                    folder_key,
                    0,
                )
                or 0
            ),
        )

    except (
        TypeError,
        ValueError,
    ):

        return 0


def _record_folder_cursor(
    *,
    email_account,
    folder_key,
    uid,
    uidvalidity,
):
    state = (
        dict(
            email_account
            .last_synced_uids
        )
        if isinstance(
            email_account
            .last_synced_uids,
            dict,
        )
        else {}
    )


    validity_state = (
        dict(
            state.get(
                "_uidvalidity",
                {},
            )
        )
        if isinstance(
            state.get(
                "_uidvalidity",
                {},
            ),
            dict,
        )
        else {}
    )


    state[
        folder_key
    ] = int(
        uid
        or 0
    )


    if uidvalidity:

        validity_state[
            folder_key
        ] = str(
            uidvalidity
        )


    state[
        "_uidvalidity"
    ] = validity_state


    email_account.last_synced_uids = (
        state
    )


    email_account.save(
        update_fields=[
            "last_synced_uids",
        ]
    )


def _search_folder_uids(
    mail,
    *,
    last_uid,
    cutoff,
):
    if last_uid > 0:

        criteria = (
            "(UID "
            + str(
                last_uid + 1
            )
            + ":*)"
        )

    else:

        criteria = (
            '(SINCE "'
            + cutoff.strftime(
                "%d-%b-%Y"
            )
            + '")'
        )


    status, messages = (
        mail.uid(
            "search",
            None,
            criteria,
        )
    )


    if status != "OK":

        raise RuntimeError(
            "Unable to search IMAP mailbox."
        )


    if (
        not messages
        or
        not messages[0]
    ):

        return []


    return [
        value
        for value in (
            messages[0]
            .split()
        )
        if value
    ]


def _imap_conversation_key(
    *,
    email_account,
    thread_identity,
):
    digest = (
        hashlib.sha256(
            str(
                thread_identity
                or ""
            )
            .casefold()
            .encode(
                "utf-8"
            )
        )
        .hexdigest()
    )


    return (
        "imap_"
        + str(
            email_account.id
        )
        + "_"
        + digest
    )


def _resolve_imap_conversation(
    *,
    user,
    organization,
    email_account,
    thread_identity,
    subject,
    local_message=None,
):
    conversation_key = (
        _imap_conversation_key(
            email_account=(
                email_account
            ),
            thread_identity=(
                thread_identity
            ),
        )
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


    if conversation is not None:

        return conversation


    local_conversation = (
        local_message.conversation
        if (
            local_message
            and
            local_message
            .conversation_id
        )
        else None
    )


    if local_conversation is not None:

        local_conversation.organization = (
            organization
        )

        local_conversation.email_account = (
            email_account
        )

        local_conversation.conversation_key = (
            conversation_key
        )

        local_conversation.external_conversation_id = (
            _bounded_identity(
                thread_identity
            )
        )

        if subject:

            local_conversation.subject = (
                subject
            )


        local_conversation.save(
            update_fields=[
                "organization",
                "email_account",
                "conversation_key",
                "external_conversation_id",
                "subject",
            ]
        )


        return (
            local_conversation
        )


    return (
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
                _bounded_identity(
                    thread_identity
                )
            ),
            subject=(
                subject
                or
                "No Subject"
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
        or
        conversation.subject
    )


    conversation.save(
        update_fields=[
            "last_message",
            "last_message_at",
            "last_message_preview",
            "subject",
        ]
    )


def _priority_state(
    *,
    subject,
    body,
):
    high = (
        "urgent",
        "asap",
        "immediately",
        "critical",
        "action required",
    )

    medium = (
        "invoice",
        "payment",
        "due",
        "deadline",
        "important",
    )


    combined = (
        (
            str(
                subject
                or ""
            )
            + " "
            + str(
                body
                or ""
            )
        )
        .lower()
    )


    score = 0


    for word in high:

        if word in combined:

            score += 40


    for word in medium:

        if word in combined:

            score += 20


    if (
        subject
        and
        subject.isupper()
    ):

        score += 10


    score = min(
        score,
        100,
    )


    return (
        score >= 50,
        score,
    )


# ================================
# IMAP FETCH
# ================================

def fetch_imap_emails(
    *,
    user,
    email_account,
    password,
    limit=None,
):
    """
    Governed Other Work Email ingestion.

    Initial history:
    - bounded by the existing 90-day mail sync policy
    - Inbox + Sent only
    - complete unless an explicit test/diagnostic limit is used

    Incremental history:
    - UID based
    - UIDVALIDITY aware
    - RFC Message-ID remains the stable deduplication identity
    """

    if email_account is None:

        raise ValueError(
            "IMAP EmailAccount does not exist"
        )


    if (
        email_account.user_id
        !=
        user.id
    ):

        raise ValueError(
            "IMAP mailbox ownership mismatch."
        )


    if (
        email_account.account_type
        !=
        "imap"
    ):

        return {
            "status":
                "skipped",

            "reason":
                "not_imap",
        }


    organization = (
        email_account.organization
    )


    membership = (
        getattr(
            user,
            "organization_membership",
            None,
        )
    )


    if (
        membership is None
        or
        organization.id
        !=
        membership.organization_id
    ):

        raise ValueError(
            "IMAP mailbox workspace mismatch."
        )


    update_sync_status(
        user=user,
        platform="imap",
        status="syncing",
        progress=0,
        error_message="",
    )


    mail = None


    try:

        endpoint = (
            validate_mailbox_endpoint(
                host=(
                    email_account
                    .imap_server
                ),
                port=(
                    email_account
                    .imap_port
                ),
                protocol="imap",
            )
        )


        mail = (
            _PinnedIMAP4SSL(
                endpoint
            )
        )


        mail.login(
            email_account.email_address,
            password,
        )


        status, folder_list = (
            mail.list()
        )


        if status != "OK":

            raise RuntimeError(
                "Unable to fetch IMAP folder list."
            )


        folder_config = (
            _discover_imap_folders(
                folder_list
            )
        )


        window = (
            resolve_mail_sync_window(
                email_account=(
                    email_account
                )
            )
        )


        state = (
            email_account
            .last_synced_uids
            if isinstance(
                email_account
                .last_synced_uids,
                dict,
            )
            else {}
        )


        # First establish that both required folders can be
        # selected and searched before persisting any message.
        folder_batches = []


        for config in (
            folder_config
        ):

            status, _ = (
                mail.select(
                    _quote_imap_mailbox(
                        config[
                            "folder_name"
                        ]
                    )
                )
            )


            if status != "OK":

                raise RuntimeError(
                    "Unable to select required IMAP "
                    + config[
                        "folder_key"
                    ]
                    + " folder."
                )


            uidvalidity = (
                _current_uidvalidity(
                    mail
                )
            )


            if window.initial_history:

                last_uid = 0

            else:

                last_uid = (
                    _folder_last_uid(
                        state,
                        folder_key=(
                            config[
                                "folder_key"
                            ]
                        ),
                        uidvalidity=(
                            uidvalidity
                        ),
                    )
                )


            uids = (
                _search_folder_uids(
                    mail,
                    last_uid=(
                        last_uid
                    ),
                    cutoff=(
                        window.cutoff
                    ),
                )
            )


            if limit is not None:

                try:

                    bounded_limit = max(
                        0,
                        int(
                            limit
                        ),
                    )

                except (
                    TypeError,
                    ValueError,
                ):

                    raise ValueError(
                        "IMAP sync limit must be an integer."
                    )


                if bounded_limit == 0:

                    uids = []

                else:

                    uids = (
                        uids[
                            -bounded_limit:
                        ]
                    )


            folder_batches.append(
                {
                    **config,

                    "uidvalidity":
                        uidvalidity,

                    "last_uid":
                        last_uid,

                    "uids":
                        uids,
                }
            )


        processed_count = 0

        created_count = 0

        upgraded_count = 0

        skipped_count = 0

        failed_count = 0


        for batch in (
            folder_batches
        ):

            folder_key = (
                batch[
                    "folder_key"
                ]
            )

            folder_name = (
                batch[
                    "folder_name"
                ]
            )

            direction = (
                batch[
                    "direction"
                ]
            )


            status, _ = (
                mail.select(
                    _quote_imap_mailbox(
                        folder_name
                    )
                )
            )


            if status != "OK":

                raise RuntimeError(
                    "Required IMAP folder became unavailable."
                )


            current_validity = (
                _current_uidvalidity(
                    mail
                )
            )


            if (
                batch[
                    "uidvalidity"
                ]
                and
                current_validity
                and
                str(
                    batch[
                        "uidvalidity"
                    ]
                )
                !=
                str(
                    current_validity
                )
            ):

                raise RuntimeError(
                    "IMAP UIDVALIDITY changed during synchronization."
                )


            folder_failed = False

            highest_uid = (
                batch[
                    "last_uid"
                ]
            )


            for uid in (
                batch[
                    "uids"
                ]
            ):

                uid_text = (
                    uid.decode(
                        "ascii",
                        errors="ignore",
                    )
                    if isinstance(
                        uid,
                        bytes,
                    )
                    else str(uid)
                )


                try:

                    status, message_data = (
                        mail.uid(
                            "fetch",
                            uid,
                            (
                                "(RFC822 FLAGS "
                                "INTERNALDATE)"
                            ),
                        )
                    )


                    if (
                        status != "OK"
                        or
                        not message_data
                        or
                        not isinstance(
                            message_data[0],
                            tuple,
                        )
                        or
                        len(
                            message_data[0]
                        ) < 2
                    ):

                        raise RuntimeError(
                            "Unable to fetch IMAP message."
                        )


                    raw_metadata = (
                        message_data[0][0]
                    )

                    raw_email = (
                        message_data[0][1]
                    )


                    if isinstance(
                        raw_metadata,
                        bytes,
                    ):

                        metadata_text = (
                            raw_metadata.decode(
                                "utf-8",
                                errors="replace",
                            )
                        )

                    else:

                        metadata_text = str(
                            raw_metadata
                            or ""
                        )


                    message = (
                        email.message_from_bytes(
                            raw_email
                        )
                    )


                    processed_count += 1


                    received_at = (
                        _message_timestamp(
                            message,
                            metadata_text,
                        )
                    )


                    subject = (
                        _decode_header_value(
                            message.get(
                                "Subject",
                                "",
                            )
                        )
                        .strip()
                        or
                        "No Subject"
                    )


                    (
                        sender_meta,
                        recipient_meta,
                    ) = (
                        _message_identities(
                            message
                        )
                    )


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


                    if not sender:

                        raise RuntimeError(
                            "IMAP inbound message "
                            "does not contain a valid sender."
                        )


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


                    body = (
                        _extract_imap_body(
                            message
                        )
                    )


                    attachments = (
                        _extract_imap_attachments(
                            message
                        )
                    )


                    stable_external_id = (
                        _stable_external_message_id(
                            email_account=(
                                email_account
                            ),
                            folder_key=(
                                folder_key
                            ),
                            uid=(
                                uid_text
                            ),
                            uidvalidity=(
                                current_validity
                                or
                                batch[
                                    "uidvalidity"
                                ]
                            ),
                            message=(
                                message
                            ),
                        )
                    )


                    legacy_external_id = (
                        folder_key
                        + "_"
                        + uid_text
                    )


                    existing = (
                        InboxMessage.objects
                        .filter(
                            user=user,
                            email_account=(
                                email_account
                            ),
                            external_message_id=(
                                stable_external_id
                            ),
                        )
                        .first()
                    )


                    if existing is None:

                        existing = (
                            InboxMessage.objects
                            .filter(
                                user=user,
                                email_account=(
                                    email_account
                                ),
                                external_message_id=(
                                    legacy_external_id
                                ),
                            )
                            .first()
                        )


                    was_legacy = (
                        existing is not None
                        and
                        existing.external_message_id
                        !=
                        stable_external_id
                    )


                    thread_identity = (
                        _thread_identity(
                            message,
                            fallback=(
                                stable_external_id
                            ),
                        )
                    )


                    external_thread_id = (
                        _bounded_identity(
                            thread_identity
                        )
                    )


                    in_reply_to = (
                        _bounded_identity(
                            _first_message_id(
                                message.get(
                                    "In-Reply-To"
                                )
                            )
                        )
                        or
                        None
                    )


                    conversation = (
                        _resolve_imap_conversation(
                            user=user,
                            organization=(
                                organization
                            ),
                            email_account=(
                                email_account
                            ),
                            thread_identity=(
                                thread_identity
                            ),
                            subject=(
                                subject
                            ),
                            local_message=(
                                existing
                            ),
                        )
                    )


                    flags = (
                        metadata_text
                    )


                    is_starred = (
                        r"\Flagged"
                        in
                        flags
                    )


                    is_read = (
                        True
                        if (
                            direction
                            ==
                            "outbound"
                        )
                        else
                        (
                            r"\Seen"
                            in
                            flags
                        )
                    )


                    (
                        is_priority,
                        priority_score,
                    ) = (
                        _priority_state(
                            subject=subject,
                            body=body,
                        )
                    )


                    if existing is None:

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
                                platform="imap",
                                folder=(
                                    folder_key
                                ),
                                direction=(
                                    direction
                                ),
                                external_message_id=(
                                    stable_external_id
                                ),
                                external_conversation_id=(
                                    external_thread_id
                                ),
                                in_reply_to=(
                                    in_reply_to
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
                                subject=(
                                    subject
                                ),
                                body=body,
                                attachment_meta=(
                                    attachments
                                ),
                                received_at=(
                                    received_at
                                ),
                                is_read=(
                                    is_read
                                ),
                                is_starred=(
                                    is_starred
                                ),
                                is_priority=(
                                    is_priority
                                ),
                                priority_score=(
                                    priority_score
                                ),
                                is_draft=False,
                                status=(
                                    "sent"
                                    if (
                                        direction
                                        ==
                                        "outbound"
                                    )
                                    else
                                    "queued"
                                ),
                            )
                        )


                        created_count += 1

                        should_process = True


                    else:

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
                            "imap"
                        )

                        message_obj.folder = (
                            folder_key
                        )

                        message_obj.direction = (
                            direction
                        )

                        message_obj.external_message_id = (
                            stable_external_id
                        )

                        message_obj.external_conversation_id = (
                            external_thread_id
                        )

                        message_obj.in_reply_to = (
                            in_reply_to
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
                            is_read
                        )

                        message_obj.is_starred = (
                            is_starred
                        )

                        message_obj.is_priority = (
                            is_priority
                        )

                        message_obj.priority_score = (
                            priority_score
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
                                "direction",
                                "external_message_id",
                                "external_conversation_id",
                                "in_reply_to",
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
                                "is_priority",
                                "priority_score",
                                "is_draft",
                                "status",
                            ]
                        )


                        if was_legacy:

                            upgraded_count += 1

                            should_process = True

                        else:

                            skipped_count += 1

                            should_process = False


                    _update_conversation_if_newer(
                        conversation=(
                            conversation
                        ),
                        message=(
                            message_obj
                        ),
                    )


                    refresh_conversation_local_state(
                        conversation
                    )


                    invalidate_conversation_cache(
                        user.id
                    )


                    if should_process:

                        try:

                            MessageProcessor().process_message(
                                organization=(
                                    organization
                                ),
                                message=(
                                    message_obj
                                ),
                                sender=(
                                    message_obj.sender
                                ),
                                subject=(
                                    message_obj.subject
                                ),
                                body=(
                                    message_obj.body
                                ),
                                source_channel="imap",
                            )

                        except Exception as exc:

                            log_event(
                                logger,
                                "warning",
                                "imap.knowledge.failed",
                                provider="imap",
                                account_id=(
                                    email_account.id
                                ),
                                message_id=(
                                    message_obj.id
                                ),
                                error_type=(
                                    type(exc).__name__
                                ),
                            )


                    try:

                        highest_uid = max(
                            highest_uid,
                            int(
                                uid_text
                            ),
                        )

                    except ValueError:

                        raise RuntimeError(
                            "IMAP returned an invalid UID."
                        )


                except Exception as exc:

                    failed_count += 1

                    folder_failed = True


                    log_event(
                        logger,
                        "warning",
                        "imap.message.failed",
                        provider="imap",
                        account_id=(
                            email_account.id
                        ),
                        folder=(
                            folder_key
                        ),
                        uid=(
                            uid_text
                        ),
                        error_type=(
                            type(exc).__name__
                        ),
                    )


            if folder_failed:

                raise RuntimeError(
                    "IMAP partial sync failure: "
                    + str(
                        failed_count
                    )
                    + " message(s) failed."
                )


            _record_folder_cursor(
                email_account=(
                    email_account
                ),
                folder_key=(
                    folder_key
                ),
                uid=(
                    highest_uid
                ),
                uidvalidity=(
                    current_validity
                    or
                    batch[
                        "uidvalidity"
                    ]
                ),
            )


        # An explicit diagnostic/test limit cannot prove complete
        # initial history.
        if (
            window.initial_history
            and
            limit is None
        ):

            mark_initial_history_complete(
                email_account=(
                    email_account
                )
            )


        update_sync_status(
            user=user,
            platform="imap",
            status="success",
            progress=100,
            error_message="",
        )


        return {
            "initial_history":
                window.initial_history,

            "history_complete":
                bool(
                    email_account
                    .history_sync_completed_at
                    or
                    (
                        window.initial_history
                        and
                        limit is None
                    )
                ),

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


    except Exception as exc:

        update_sync_status(
            user=user,
            platform="imap",
            status="failed",
            progress=0,
            error_message=(
                "IMAP synchronization failed."
            ),
        )


        log_event(
            logger,
            "error",
            "imap.sync.failed",
            provider="imap",
            account_id=(
                email_account.id
            ),
            error_type=(
                type(exc).__name__
            ),
        )


        try:

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
                            "sync_failed"
                    },
                },
            )

        except Exception:

            pass


        raise


    finally:

        if mail is not None:

            try:

                mail.logout()

            except Exception:

                pass


# ================================
# SMTP SEND
# ================================

import smtplib
import socket

from email.message import EmailMessage


class _PinnedSMTPSSL(
    smtplib.SMTP_SSL
):
    """
    SMTP TLS client whose TCP connection is pinned to the
    validated address set while certificate hostname
    verification uses the configured SMTP hostname.
    """

    def __init__(
        self,
        endpoint,
        *,
        timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
        source_address=None,
    ):
        self._validated_endpoint = (
            endpoint
        )

        super().__init__(
            endpoint.host,
            endpoint.port,
            timeout=timeout,
            source_address=source_address,
            context=(
                create_verified_tls_context()
            ),
        )

    def _get_socket(
        self,
        host,
        port,
        timeout,
    ):
        raw_socket = (
            connect_validated_mailbox_endpoint(
                endpoint=(
                    self._validated_endpoint
                ),
                timeout=timeout,
                source_address=(
                    self.source_address
                ),
            )
        )

        try:
            return (
                self.context
                .wrap_socket(
                    raw_socket,
                    server_hostname=(
                        self._host
                    ),
                )
            )

        except Exception:
            raw_socket.close()
            raise


def send_via_smtp(
    *,
    email_account,
    to_email,
    subject,
    body,
    inbox_message=None,
    password=None
):

    try:
        if not password:
            raise ValueError("SMTP password not configured")

        smtp_endpoint = (
            validate_mailbox_endpoint(
                host=(
                    email_account
                    .smtp_server
                ),
                port=(
                    email_account
                    .smtp_port
                ),
                protocol="smtp",
            )
        )

        msg = EmailMessage()
        msg["From"] = email_account.email_address
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(body)

        server = _PinnedSMTPSSL(
            smtp_endpoint
        )

        server.login(email_account.email_address, password)
        server.send_message(msg)
        server.quit()

        if inbox_message:
            inbox_message.status = "sent"
            inbox_message.last_attempt_at = timezone.now()
            inbox_message.save()

            create_notification(
                user=inbox_message.user,
                title="Email sent",
                message=f"Your email '{inbox_message.subject}' was sent successfully.",
                notification_type="success",
            )

    except Exception as e:

        if inbox_message:
            inbox_message.status = "failed"
            inbox_message.error_reason = str(e)
            inbox_message.retry_count += 1
            inbox_message.last_attempt_at = timezone.now()
            inbox_message.save()

            create_notification(
                user=inbox_message.user,
                title="Email failed",
                message=f"Failed to send email '{inbox_message.subject}'.",
                notification_type="error",
            )

        raise
