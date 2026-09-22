import re
import email

from datetime import timedelta

from django.db import transaction

from email_accounts.services.credential_vault import (
    CredentialVaultError,
)

from email_accounts.services.imap_smtp import (
    _PinnedIMAP4SSL,
    _current_uidvalidity,
    _discover_imap_folders,
    _first_message_id,
    _folder_last_uid,
    _mailbox_leaf,
    _parse_imap_list_entry,
    _quote_imap_mailbox,
    _record_folder_cursor,
    _search_folder_uids,
    _stable_external_message_id,
)

from email_accounts.services.mailbox_network_policy import (
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
    resolve_mail_sync_window,
)

from inbox.utils.sync_lock import (
    acquire_sync_lock,
    release_sync_lock,
)

from platform_core.observability.logger import (
    get_logger,
    log_event,
)


logger = get_logger(
    "oneuch.runtime.imap_convergence"
)


IMAP_TRASH_ALIASES = (
    "trash",
    "deleted items",
    "deleted messages",
    "deleted",
)


class IMAPConvergenceError(RuntimeError):
    pass


def _discover_imap_trash_folder(folder_list):
    entries = []

    for raw in folder_list or []:
        entry = _parse_imap_list_entry(raw)

        if entry is not None:
            entries.append(entry)

    special = [
        entry
        for entry in entries
        if r"\trash" in entry["flags"]
    ]

    if len(special) > 1:
        raise IMAPConvergenceError(
            "IMAP Trash folder discovery is ambiguous."
        )

    if special:
        return {
            "folder_key": "trash",
            "folder_name": special[0]["name"],
        }

    for alias in IMAP_TRASH_ALIASES:
        matches = [
            entry
            for entry in entries
            if _mailbox_leaf(entry) == alias
        ]

        if len(matches) > 1:
            raise IMAPConvergenceError(
                "IMAP Trash folder discovery is ambiguous."
            )

        if matches:
            return {
                "folder_key": "trash",
                "folder_name": matches[0]["name"],
            }

    return None


def _imap_credential(email_account):
    if (
        email_account is None
        or email_account.account_type != "imap"
        or not email_account.is_active
    ):
        raise IMAPConvergenceError(
            "IMAP mailbox is unavailable."
        )

    if not email_account.is_credential_valid():
        raise IMAPConvergenceError(
            "IMAP mailbox credential is unavailable."
        )

    try:
        credential = email_account.get_credential()

    except CredentialVaultError as exc:
        raise IMAPConvergenceError(
            "IMAP mailbox credential is unavailable."
        ) from exc

    if not credential:
        raise IMAPConvergenceError(
            "IMAP mailbox credential is unavailable."
        )

    return credential


def _open_imap_mailbox(email_account, *, timeout=None):
    credential = _imap_credential(email_account)

    endpoint = validate_mailbox_endpoint(
        host=email_account.imap_server,
        port=email_account.imap_port,
        protocol="imap",
    )

    mail = _PinnedIMAP4SSL(
        endpoint,
        timeout=timeout,
    )

    try:
        status, _ = mail.login(
            email_account.email_address,
            credential,
        )

        if status != "OK":
            raise IMAPConvergenceError(
                "IMAP mailbox login failed."
            )

        return mail

    except Exception:
        try:
            mail.logout()
        except Exception:
            pass

        raise


def _imap_capabilities(mail):
    status, values = mail.capability()

    if status != "OK":
        raise IMAPConvergenceError(
            "Unable to inspect IMAP capabilities."
        )

    capabilities = set()

    for value in values or []:
        if isinstance(value, bytes):
            text = value.decode(
                "ascii",
                errors="ignore",
            )
        else:
            text = str(value or "")

        capabilities.update(
            token.upper()
            for token in text.split()
            if token
        )

    return capabilities


def _uid_text(uid):
    if isinstance(uid, bytes):
        return uid.decode(
            "ascii",
            errors="ignore",
        )

    return str(uid)


def _folder_uids(mail):
    status, values = mail.uid(
        "search",
        None,
        "ALL",
    )

    if status != "OK":
        raise IMAPConvergenceError(
            "Unable to search IMAP folder."
        )

    if not values or not values[0]:
        return []

    return values[0].split()


def _message_identity_for_uid(
    *,
    mail,
    email_account,
    folder_key,
    uid,
    uidvalidity,
    include_message_id=False,
):
    raw_header = None

    for attempt in range(2):
        status, message_data = mail.uid(
            "fetch",
            uid,
            (
                "(BODY.PEEK[HEADER.FIELDS "
                "(MESSAGE-ID)])"
            ),
        )

        if status != "OK":
            raise IMAPConvergenceError(
                "Unable to fetch IMAP Message-ID header."
            )

        raw_header = None

        for item in message_data or []:
            if (
                isinstance(item, tuple)
                and len(item) >= 2
                and isinstance(item[1], bytes)
            ):
                raw_header = item[1]
                break

        if raw_header is not None:
            break

        if attempt == 0:
            continue

        raise IMAPConvergenceError(
            "IMAP Message-ID header response is invalid."
        )

    message = email.message_from_bytes(
        raw_header
    )

    message_id = _first_message_id(
        message.get("Message-ID")
    )

    if not message_id:
        if include_message_id:
            return (
                None,
                "",
            )

        return None

    identity = _stable_external_message_id(
        email_account=email_account,
        folder_key=folder_key,
        uid=_uid_text(uid),
        uidvalidity=(
            uidvalidity
            or "unknown"
        ),
        message=message,
    )

    if include_message_id:
        return (
            identity,
            message_id,
        )

    return identity



IMAP_INTERACTIVE_TRASH_TIMEOUT_SECONDS = 20

IMAP_DELETE_NARROW_MAX_CANDIDATES = 50

IMAP_DELETE_BROAD_MAX_CANDIDATES = 100


def _local_rfc_message_id_candidate(
    *,
    email_account,
    local_message,
):
    """
    Recover a raw RFC Message-ID only when local metadata
    mathematically resolves to the exact stored stable
    external_message_id.
    """

    target_identity = (
        str(
            local_message.external_message_id
            or ""
        )
        .strip()
    )

    source = (
        str(
            local_message.external_conversation_id
            or ""
        )
        .strip()
    )

    candidate = (
        _first_message_id(
            source
        )
    )

    if (
        not candidate
        or
        not target_identity.startswith(
            "imap-rfc822-"
        )
    ):
        return ""


    parsed = (
        email.message_from_string(
            "Message-ID: "
            + candidate
            + "\n\n"
        )
    )


    calculated = (
        _stable_external_message_id(
            email_account=(
                email_account
            ),
            folder_key="inbox",
            uid="0",
            uidvalidity="unknown",
            message=parsed,
        )
    )


    if calculated != target_identity:
        return ""


    return candidate


def _quote_imap_search_value(
    value,
):
    source = str(
        value
        or ""
    )

    return (
        '"'
        + source
        .replace(
            "\\",
            "\\\\",
        )
        .replace(
            '"',
            '\\"',
        )
        + '"'
    )


def _search_folder_for_local_messages(
    *,
    mail,
    email_account,
    folder_key,
    folder_name,
    local_messages,
    target_identities,
):
    """
    Locate known local messages without walking the whole
    provider folder.

    Preferred path:
      HEADER Message-ID provider search.

    Historical compatibility path:
      bounded provider ON + FROM + optional SUBJECT search.

    Every candidate is fetched and accepted only when its
    canonical stable identity exactly equals the local
    external_message_id.
    """

    relevant_messages = [
        item
        for item in (
            local_messages
            or []
        )
        if (
            str(
                item.external_message_id
                or ""
            ).strip()
            in target_identities
        )
    ]


    direct_candidates = {}

    fallback_messages = []


    for local_message in (
        relevant_messages
    ):

        identity = (
            str(
                local_message.external_message_id
                or ""
            )
            .strip()
        )


        candidate = (
            _local_rfc_message_id_candidate(
                email_account=(
                    email_account
                ),
                local_message=(
                    local_message
                ),
            )
        )


        if candidate:

            direct_candidates[
                identity
            ] = candidate

        else:

            fallback_messages.append(
                local_message
            )


    found = {}


    # --------------------------------------------------------
    # Fast exact Message-ID path
    # --------------------------------------------------------

    if direct_candidates:

        direct_found = (
            _search_folder_for_candidate_identities(
                mail=mail,
                email_account=(
                    email_account
                ),
                folder_key=(
                    folder_key
                ),
                folder_name=(
                    folder_name
                ),
                candidate_message_ids=(
                    direct_candidates
                ),
            )
        )


        for (
            identity,
            uids,
        ) in (
            direct_found.items()
        ):

            found.setdefault(
                identity,
                [],
            ).extend(
                uids
            )


        # Some IMAP providers do not reliably return an exact
        # HEADER Message-ID search hit even when that header is
        # present. If the direct lookup produced no verified
        # location, fall through to the bounded provider search.
        #
        # The fallback still requires exact canonical stable-ID
        # verification before any provider MOVE is authorized.
        for local_message in (
            relevant_messages
        ):

            identity = (
                str(
                    local_message.external_message_id
                    or ""
                )
                .strip()
            )

            if found.get(
                identity
            ):
                continue

            candidate = (
                _local_rfc_message_id_candidate(
                    email_account=(
                        email_account
                    ),
                    local_message=(
                        local_message
                    ),
                )
            )

            if candidate:

                fallback_messages.append(
                    local_message
                )


    if not fallback_messages:
        return found


    # --------------------------------------------------------
    # Historical rows without recoverable raw Message-ID
    # --------------------------------------------------------

    status, _ = (
        mail.select(
            _quote_imap_mailbox(
                folder_name
            )
        )
    )


    if status != "OK":

        raise IMAPConvergenceError(
            "Unable to select IMAP folder."
        )


    uidvalidity = (
        _current_uidvalidity(
            mail
        )
    )


    search_cache = {}

    identity_cache = {}


    def provider_search(
        *,
        day,
        sender,
        subject,
        narrow,
    ):

        cache_key = (
            day.isoformat(),
            sender.casefold(),
            subject.casefold(),
            bool(narrow),
        )


        if cache_key in search_cache:
            return search_cache[
                cache_key
            ]


        search_args = [
            "search",
            None,
            "ON",
            day.strftime(
                "%d-%b-%Y"
            ),
            "FROM",
            _quote_imap_search_value(
                sender
            ),
        ]


        if (
            narrow
            and
            subject
            and
            subject.casefold()
            !=
            "no subject"
        ):

            search_args.extend(
                [
                    "SUBJECT",
                    _quote_imap_search_value(
                        subject
                    ),
                ]
            )


        status, values = (
            mail.uid(
                *search_args
            )
        )


        if status != "OK":

            raise IMAPConvergenceError(
                "Unable to perform bounded "
                "IMAP provider lookup."
            )


        uids = (
            values[0].split()
            if (
                values
                and
                values[0]
            )
            else []
        )


        maximum = (
            IMAP_DELETE_NARROW_MAX_CANDIDATES
            if narrow
            else
            IMAP_DELETE_BROAD_MAX_CANDIDATES
        )


        if len(uids) > maximum:

            raise IMAPConvergenceError(
                "IMAP provider lookup returned "
                "too many candidates for a "
                "safe interactive Trash operation."
            )


        search_cache[
            cache_key
        ] = uids


        return uids


    def identity_for_uid(
        uid,
    ):

        uid_text = (
            _uid_text(
                uid
            )
        )

        key = (
            str(
                uidvalidity
                or "unknown"
            ),
            uid_text,
        )


        if key not in identity_cache:

            identity_cache[
                key
            ] = (
                _message_identity_for_uid(
                    mail=mail,
                    email_account=(
                        email_account
                    ),
                    folder_key=(
                        folder_key
                    ),
                    uid=uid,
                    uidvalidity=(
                        uidvalidity
                    ),
                )
            )


        return (
            uid_text,
            identity_cache[
                key
            ],
        )


    for local_message in (
        fallback_messages
    ):

        target_identity = (
            str(
                local_message.external_message_id
                or ""
            )
            .strip()
        )


        received_at = (
            local_message.received_at
        )


        if received_at is None:

            raise IMAPConvergenceError(
                "IMAP message does not have "
                "a safe provider lookup timestamp."
            )


        sender = (
            str(
                local_message.sender
                or ""
            )
            .strip()
        )


        if not sender:

            raise IMAPConvergenceError(
                "IMAP message does not have "
                "a safe provider lookup sender."
            )


        subject = (
            str(
                local_message.subject
                or ""
            )
            .strip()
        )


        matched_uids = set()


        for day_offset in (
            0,
            -1,
            1,
        ):

            day = (
                received_at
                + timedelta(
                    days=day_offset
                )
            ).date()


            # First try the narrow search including subject.
            narrow_uids = (
                provider_search(
                    day=day,
                    sender=sender,
                    subject=subject,
                    narrow=True,
                )
            )


            exact_found = False


            for uid in (
                narrow_uids
            ):

                (
                    uid_text,
                    identity,
                ) = identity_for_uid(
                    uid
                )


                if identity != target_identity:
                    continue


                matched_uids.add(
                    uid_text
                )

                exact_found = True


            # If subject-based search found no exact target,
            # broaden to date + sender only. Exact identity
            # verification still authorizes the result.
            if not exact_found:

                broad_uids = (
                    provider_search(
                        day=day,
                        sender=sender,
                        subject="",
                        narrow=False,
                    )
                )


                for uid in (
                    broad_uids
                ):

                    (
                        uid_text,
                        identity,
                    ) = (
                        identity_for_uid(
                            uid
                        )
                    )


                    if identity != target_identity:
                        continue


                    matched_uids.add(
                        uid_text
                    )


        if matched_uids:

            found.setdefault(
                target_identity,
                [],
            ).extend(
                sorted(
                    matched_uids,
                    key=int,
                )
            )


    return found

def _scan_folder_for_identities(
    *,
    mail,
    email_account,
    folder_key,
    folder_name,
    target_identities=None,
):
    """
    Scan one provider folder for canonical RFC Message-ID
    identities using bounded batched UID FETCH operations.

    This retains exact One UCH identity verification while
    avoiding one provider round-trip per mailbox message.
    """

    status, _ = mail.select(
        _quote_imap_mailbox(
            folder_name
        )
    )

    if status != "OK":
        raise IMAPConvergenceError(
            "Unable to select IMAP folder."
        )

    uidvalidity = _current_uidvalidity(
        mail
    )

    uids = [
        _uid_text(uid)
        for uid in _folder_uids(
            mail
        )
    ]

    found = {}

    if not uids:
        return found

    batch_size = 200

    for offset in range(
        0,
        len(uids),
        batch_size,
    ):
        batch = uids[
            offset:
            offset + batch_size
        ]

        expected = set(
            batch
        )

        uid_set = ",".join(
            batch
        )

        response_items = None

        for attempt in range(2):

            status, message_data = (
                mail.uid(
                    "fetch",
                    uid_set,
                    (
                        "(BODY.PEEK[HEADER.FIELDS "
                        "(MESSAGE-ID)])"
                    ),
                )
            )

            if status != "OK":
                raise IMAPConvergenceError(
                    "Unable to fetch IMAP Message-ID headers."
                )

            parsed_uids = set()

            response_found = {}

            for item in (
                message_data
                or []
            ):

                if (
                    not isinstance(
                        item,
                        tuple,
                    )
                    or
                    len(item) < 2
                    or
                    not isinstance(
                        item[1],
                        bytes,
                    )
                ):
                    continue

                metadata = item[0]

                if isinstance(
                    metadata,
                    bytes,
                ):
                    metadata = (
                        metadata.decode(
                            "ascii",
                            errors="ignore",
                        )
                    )

                else:
                    metadata = str(
                        metadata
                        or ""
                    )

                match = re.search(
                    r"\bUID\s+(\d+)\b",
                    metadata,
                    re.IGNORECASE,
                )

                if not match:
                    continue

                uid_text = (
                    match.group(1)
                )

                if uid_text not in expected:
                    continue

                parsed_uids.add(
                    uid_text
                )

                message = (
                    email.message_from_bytes(
                        item[1]
                    )
                )

                message_id = (
                    _first_message_id(
                        message.get(
                            "Message-ID"
                        )
                    )
                )

                if not message_id:
                    continue

                identity = (
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
                            uidvalidity
                            or "unknown"
                        ),
                        message=(
                            message
                        ),
                    )
                )

                if (
                    target_identities
                    is not None
                    and
                    identity
                    not in
                    target_identities
                ):
                    continue

                response_found.setdefault(
                    identity,
                    [],
                ).append(
                    uid_text
                )

            if parsed_uids == expected:
                response_items = (
                    response_found
                )
                break

            if attempt == 0:
                continue

            raise IMAPConvergenceError(
                "IMAP Message-ID batch response is incomplete."
            )

        for (
            identity,
            identity_uids,
        ) in (
            response_items
            or {}
        ).items():

            found.setdefault(
                identity,
                [],
            ).extend(
                identity_uids
            )

    return found

def _search_folder_for_candidate_identities(
    *,
    mail,
    email_account,
    folder_key,
    folder_name,
    candidate_message_ids,
):
    """
    Find only known Trash candidates in one active folder.

    The provider HEADER search reduces active-copy verification
    from a full-folder header walk to candidate-driven lookup.
    Every provider search hit is re-fetched and verified using
    the canonical One UCH stable Message-ID identity.
    """

    status, _ = mail.select(
        _quote_imap_mailbox(
            folder_name
        )
    )

    if status != "OK":
        raise IMAPConvergenceError(
            "Unable to select IMAP folder."
        )

    uidvalidity = _current_uidvalidity(
        mail
    )

    found = {}

    for (
        target_identity,
        message_id,
    ) in candidate_message_ids.items():

        search_value = (
            str(
                message_id
                or ""
            )
            .strip()
        )

        if not search_value:
            continue

        search_value = (
            '"'
            + search_value
            .replace(
                "\\",
                "\\\\",
            )
            .replace(
                '"',
                '\\"',
            )
            + '"'
        )

        status, values = mail.uid(
            "search",
            None,
            "HEADER",
            "Message-ID",
            search_value,
        )

        if status != "OK":
            raise IMAPConvergenceError(
                "Unable to search active IMAP Message-ID."
            )

        if (
            not values
            or
            not values[0]
        ):
            continue

        for uid in values[0].split():

            identity = (
                _message_identity_for_uid(
                    mail=mail,
                    email_account=(
                        email_account
                    ),
                    folder_key=(
                        folder_key
                    ),
                    uid=uid,
                    uidvalidity=(
                        uidvalidity
                    ),
                )
            )

            # IMAP HEADER SEARCH is substring-based.
            # Never trust the search result alone.
            if (
                identity
                !=
                target_identity
            ):
                continue

            found.setdefault(
                target_identity,
                [],
            ).append(
                _uid_text(uid)
            )

    return found


def reconcile_imap_trash(
    *,
    user,
    email_account,
):
    """
    Reconcile provider Trash -> existing One UCH messages.

    Only Message-ID headers are inspected.
    Deleted provider messages are never imported as new mail.
    """

    if (
        email_account.user_id
        != user.id
    ):
        raise IMAPConvergenceError(
            "IMAP mailbox ownership mismatch."
        )


    mail = (
        _open_imap_mailbox(
            email_account
        )
    )


    try:

        status, folder_list = (
            mail.list()
        )

        if status != "OK":
            raise IMAPConvergenceError(
                "Unable to fetch IMAP folder list."
            )


        trash = (
            _discover_imap_trash_folder(
                folder_list
            )
        )

        if trash is None:

            log_event(
                logger,
                "warning",
                "imap.trash.skipped_missing",
                account_id=(
                    email_account.id
                ),
            )

            return {
                "status":
                    "skipped",

                "reason":
                    "trash_unavailable",

                "processed":
                    0,

                "matched":
                    0,
            }


        status, _ = (
            mail.select(
                _quote_imap_mailbox(
                    trash[
                        "folder_name"
                    ]
                )
            )
        )

        if status != "OK":
            raise IMAPConvergenceError(
                "Unable to select IMAP Trash folder."
            )


        uidvalidity = (
            _current_uidvalidity(
                mail
            )
        )


        state = (
            email_account.last_synced_uids
            if isinstance(
                email_account.last_synced_uids,
                dict,
            )
            else {}
        )


        last_uid = (
            _folder_last_uid(
                state,
                folder_key="trash",
                uidvalidity=uidvalidity,
            )
        )


        window = (
            resolve_mail_sync_window(
                email_account=email_account
            )
        )


        uids = (
            _search_folder_uids(
                mail,
                last_uid=last_uid,
                cutoff=window.cutoff,
            )
        )


        identities = set()

        candidate_message_ids = {}

        highest_uid = (
            last_uid
        )


        for uid in uids:

            (
                identity,
                message_id,
            ) = (
                _message_identity_for_uid(
                    mail=mail,
                    email_account=(
                        email_account
                    ),
                    folder_key="trash",
                    uid=uid,
                    uidvalidity=uidvalidity,
                    include_message_id=True,
                )
            )

            if identity:
                identities.add(
                    identity
                )

                candidate_message_ids[
                    identity
                ] = message_id


            try:

                highest_uid = max(
                    highest_uid,
                    int(
                        _uid_text(
                            uid
                        )
                    ),
                )

            except ValueError as exc:

                raise IMAPConvergenceError(
                    "IMAP returned an invalid Trash UID."
                ) from exc


        active_identities = set()


        if identities:

            active_folders = (
                _discover_imap_folders(
                    folder_list
                )
            )


            for config in active_folders:

                active_matches = (
                    _search_folder_for_candidate_identities(
                        mail=mail,
                        email_account=(
                            email_account
                        ),
                        folder_key=(
                            config[
                                "folder_key"
                            ]
                        ),
                        folder_name=(
                            config[
                                "folder_name"
                            ]
                        ),
                        candidate_message_ids=(
                                candidate_message_ids
                            ),
                    )
                )


                active_identities.update(
                    active_matches.keys()
                )


        trash_only_identities = (
            identities
            -
            active_identities
        )


    finally:

        try:
            mail.logout()
        except Exception:
            pass


    matched_ids = []

    conversation_ids = set()


    with transaction.atomic():

        locked_account = (
            type(
                email_account
            )
            .objects
            .select_for_update()
            .get(
                id=email_account.id
            )
        )


        if trash_only_identities:

            matched = list(
                InboxMessage.objects
                .select_for_update()
                .filter(
                    user=user,
                    email_account=(
                        locked_account
                    ),
                    platform="imap",
                    external_message_id__in=(
                        trash_only_identities
                    ),
                )
                .exclude(
                    folder="trash"
                )
            )


            matched_ids = [
                message.id
                for message in matched
            ]


            conversation_ids = {
                message.conversation_id
                for message in matched
                if (
                    message.conversation_id
                    is not None
                )
            }


            if matched_ids:

                (
                    InboxMessage.objects
                    .filter(
                        id__in=matched_ids
                    )
                    .update(
                        folder="trash"
                    )
                )


        conversations = list(
            Conversation.objects
            .select_for_update()
            .filter(
                id__in=conversation_ids
            )
        )


        for conversation in conversations:

            refresh_conversation_local_state(
                conversation
            )


        _record_folder_cursor(
            email_account=(
                locked_account
            ),
            folder_key="trash",
            uid=highest_uid,
            uidvalidity=uidvalidity,
        )


    if matched_ids:

        invalidate_conversation_cache(
            user.id
        )


    log_event(
        logger,
        "info",
        "imap.trash.reconciled",
        account_id=(
            email_account.id
        ),
        processed=(
            len(uids)
        ),
        matched=(
            len(matched_ids)
        ),
    )


    return {
        "status":
            "completed",

        "processed":
            len(uids),

        "matched":
            len(matched_ids),
    }


IMAP_INTERACTIVE_FLAG_TIMEOUT_SECONDS = 20


def _set_imap_conversation_flag(
    *,
    conversation,
    user,
    flag,
    enabled,
    local_field,
    inbound_only=False,
):
    """
    Converge one One UCH conversation flag to the IMAP provider.

    Provider mutation completes before local state is changed.
    Existing stable-message identity verification is reused so
    One UCH never mutates a provider UID merely by position.
    """

    if (
        conversation is None
        or conversation.user_id
        != user.id
    ):
        raise IMAPConvergenceError(
            "Conversation ownership mismatch."
        )


    account = (
        conversation.email_account
    )


    if (
        account is None
        or account.account_type
        != "imap"
        or not account.is_active
        or account.user_id
        != user.id
    ):
        raise IMAPConvergenceError(
            "Conversation IMAP mailbox is unavailable."
        )


    lock = (
        acquire_sync_lock(
            account.id
        )
    )


    if not lock:
        raise IMAPConvergenceError(
            "Mailbox is currently synchronizing. "
            "Please retry shortly."
        )


    mail = None


    try:

        queryset = (
            conversation.messages
            .filter(
                user=user,
                organization=(
                    conversation.organization
                ),
                email_account=account,
                platform="imap",
                is_draft=False,
            )
            .exclude(
                folder="trash"
            )
        )


        if inbound_only:

            queryset = (
                queryset.filter(
                    direction="inbound"
                )
            )


        messages = list(
            queryset.order_by(
                "id"
            )
        )


        if not messages:

            return {
                "status":
                    "completed",

                "updated":
                    0,

                "provider_updates":
                    0,
            }


        message_ids = [
            message.id
            for message in messages
        ]


        target_identities = {
            str(
                message.external_message_id
                or ""
            ).strip()
            for message in messages
        }


        if (
            not target_identities
            or any(
                not identity
                or not (
                    identity.startswith(
                        "imap-rfc822-"
                    )
                    or identity.startswith(
                        "imap-uid-"
                    )
                )
                for identity
                in target_identities
            )
        ):
            raise IMAPConvergenceError(
                "Conversation contains an IMAP "
                "message without a safe provider identity."
            )


        mail = (
            _open_imap_mailbox(
                account,
                timeout=(
                    IMAP_INTERACTIVE_FLAG_TIMEOUT_SECONDS
                ),
            )
        )


        status, folder_list = (
            mail.list()
        )


        if status != "OK":
            raise IMAPConvergenceError(
                "Unable to fetch IMAP folder list."
            )


        active_folders = (
            _discover_imap_folders(
                folder_list
            )
        )


        locations = {}


        for config in active_folders:

            locations[
                config["folder_name"]
            ] = (
                _search_folder_for_local_messages(
                    mail=mail,
                    email_account=account,
                    folder_key=(
                        config["folder_key"]
                    ),
                    folder_name=(
                        config["folder_name"]
                    ),
                    local_messages=messages,
                    target_identities=(
                        target_identities
                    ),
                )
            )


        provider_identities = set()


        for folder_map in (
            locations.values()
        ):

            provider_identities.update(
                folder_map.keys()
            )


        missing = (
            target_identities
            -
            provider_identities
        )


        if missing:
            raise IMAPConvergenceError(
                "One or more conversation messages "
                "could not be located in the "
                "IMAP mailbox."
            )


        operation = (
            "+FLAGS.SILENT"
            if enabled
            else "-FLAGS.SILENT"
        )


        provider_updates = 0


        for config in active_folders:

            folder_name = (
                config["folder_name"]
            )

            folder_map = (
                locations[
                    folder_name
                ]
            )


            if not folder_map:
                continue


            status, _ = (
                mail.select(
                    _quote_imap_mailbox(
                        folder_name
                    )
                )
            )


            if status != "OK":
                raise IMAPConvergenceError(
                    "Unable to select IMAP folder "
                    "for flag mutation."
                )


            for identity in (
                target_identities
            ):

                for uid in (
                    folder_map.get(
                        identity,
                        [],
                    )
                ):

                    status, _ = (
                        mail.uid(
                            "STORE",
                            uid,
                            operation,
                            (
                                "("
                                + flag
                                + ")"
                            ),
                        )
                    )


                    if status != "OK":
                        raise IMAPConvergenceError(
                            "IMAP provider flag "
                            "mutation failed."
                        )


                    provider_updates += 1


        with transaction.atomic():

            locked_messages = (
                InboxMessage.objects
                .select_for_update()
                .filter(
                    id__in=message_ids,
                    user=user,
                    organization=(
                        conversation.organization
                    ),
                    email_account=account,
                    platform="imap",
                    is_draft=False,
                )
                .exclude(
                    folder="trash"
                )
            )


            if (
                locked_messages.count()
                !=
                len(message_ids)
            ):
                raise IMAPConvergenceError(
                    "Conversation changed while "
                    "IMAP flag mutation was executing."
                )


            locked_messages.update(
                **{
                    local_field:
                        enabled
                }
            )


            locked_conversation = (
                Conversation.objects
                .select_for_update()
                .get(
                    id=conversation.id
                )
            )


            refresh_conversation_local_state(
                locked_conversation
            )


        invalidate_conversation_cache(
            user.id
        )


        log_event(
            logger,
            "info",
            "imap.flag.conversation_updated",
            account_id=(
                account.id
            ),
            conversation_id=(
                conversation.id
            ),
            flag=flag,
            enabled=bool(enabled),
            provider_updates=(
                provider_updates
            ),
            local_updates=(
                len(message_ids)
            ),
        )


        return {
            "status":
                "completed",

            "updated":
                len(message_ids),

            "provider_updates":
                provider_updates,
        }


    finally:

        if mail is not None:

            try:
                mail.logout()

            except Exception:
                pass


        release_sync_lock(
            lock
        )


def set_imap_conversation_read(
    *,
    conversation,
    user,
    is_read,
):
    if not isinstance(
        is_read,
        bool,
    ):
        raise IMAPConvergenceError(
            "is_read must be boolean."
        )


    return _set_imap_conversation_flag(
        conversation=conversation,
        user=user,
        flag=r"\Seen",
        enabled=is_read,
        local_field="is_read",
        inbound_only=True,
    )


def set_imap_conversation_star(
    *,
    conversation,
    user,
    is_starred,
):
    if not isinstance(
        is_starred,
        bool,
    ):
        raise IMAPConvergenceError(
            "is_starred must be boolean."
        )


    return _set_imap_conversation_flag(
        conversation=conversation,
        user=user,
        flag=r"\Flagged",
        enabled=is_starred,
        local_field="is_starred",
        inbound_only=False,
    )


def trash_imap_conversation(
    *,
    conversation,
    user,
):
    """
    Move one One UCH IMAP conversation to provider Trash.

    Provider matching uses the stable RFC Message-ID identity.
    Local rows are changed only after provider locations are
    validated and all requested MOVE operations have succeeded.
    """

    if (
        conversation is None
        or conversation.user_id
        != user.id
    ):
        raise IMAPConvergenceError(
            "Conversation ownership mismatch."
        )


    account = (
        conversation.email_account
    )


    if (
        account is None
        or account.account_type
        != "imap"
        or not account.is_active
        or account.user_id
        != user.id
    ):
        raise IMAPConvergenceError(
            "Conversation IMAP mailbox is unavailable."
        )


    lock = (
        acquire_sync_lock(
            account.id
        )
    )


    if not lock:
        raise IMAPConvergenceError(
            "Mailbox is currently synchronizing. "
            "Please retry shortly."
        )


    mail = None


    try:

        messages = list(
            conversation.messages
            .filter(
                user=user,
                organization=(
                    conversation.organization
                ),
                email_account=account,
                platform="imap",
                is_draft=False,
            )
            .exclude(
                folder="trash"
            )
            .order_by(
                "id"
            )
        )


        if not messages:
            return {
                "status":
                    "completed",

                "updated":
                    0,

                "moved":
                    0,
            }


        message_ids = [
            message.id
            for message in messages
        ]


        target_identities = {
            str(
                message.external_message_id
                or ""
            ).strip()
            for message in messages
        }


        if (
            not target_identities
            or any(
                not identity.startswith(
                    "imap-rfc822-"
                )
                for identity
                in target_identities
            )
        ):
            raise IMAPConvergenceError(
                "Conversation contains an IMAP "
                "message without a safe RFC "
                "Message-ID identity."
            )


        mail = (
            _open_imap_mailbox(
                account,
                timeout=(
                    IMAP_INTERACTIVE_TRASH_TIMEOUT_SECONDS
                ),
            )
        )


        capabilities = (
            _imap_capabilities(
                mail
            )
        )


        if "MOVE" not in capabilities:
            raise IMAPConvergenceError(
                "IMAP provider does not "
                "support UID MOVE."
            )


        status, folder_list = (
            mail.list()
        )


        if status != "OK":
            raise IMAPConvergenceError(
                "Unable to fetch IMAP folder list."
            )


        trash = (
            _discover_imap_trash_folder(
                folder_list
            )
        )


        if trash is None:
            raise IMAPConvergenceError(
                "Unable to discover IMAP Trash folder."
            )


        active_folders = (
            _discover_imap_folders(
                folder_list
            )
        )


        active_locations = {}


        for config in active_folders:

            active_locations[
                config[
                    "folder_name"
                ]
            ] = (
                _search_folder_for_local_messages(
                    mail=mail,
                    email_account=account,
                    folder_key=(
                        config[
                            "folder_key"
                        ]
                    ),
                    folder_name=(
                        config[
                            "folder_name"
                        ]
                    ),
                    local_messages=(
                        messages
                    ),
                    target_identities=(
                        target_identities
                    ),
                )
            )


        trash_locations = (
            _search_folder_for_local_messages(
                mail=mail,
                email_account=account,
                folder_key="trash",
                folder_name=(
                    trash[
                        "folder_name"
                    ]
                ),
                local_messages=(
                    messages
                ),
                target_identities=(
                    target_identities
                ),
            )
        )


        provider_identities = set(
            trash_locations
        )


        for folder_map in (
            active_locations.values()
        ):
            provider_identities.update(
                folder_map.keys()
            )


        missing = (
            target_identities
            -
            provider_identities
        )


        if missing:
            raise IMAPConvergenceError(
                "One or more conversation messages "
                "could not be located in the "
                "IMAP mailbox."
            )


        moved_count = 0


        for config in active_folders:

            folder_name = (
                config[
                    "folder_name"
                ]
            )

            folder_map = (
                active_locations[
                    folder_name
                ]
            )


            if not folder_map:
                continue


            status, _ = (
                mail.select(
                    _quote_imap_mailbox(
                        folder_name
                    )
                )
            )


            if status != "OK":
                raise IMAPConvergenceError(
                    "Unable to select IMAP "
                    "source folder for Trash."
                )


            for identity in target_identities:

                for uid in (
                    folder_map.get(
                        identity,
                        [],
                    )
                ):

                    status, _ = (
                        mail.uid(
                            "MOVE",
                            uid,
                            _quote_imap_mailbox(
                                trash[
                                    "folder_name"
                                ]
                            ),
                        )
                    )


                    if status != "OK":
                        raise IMAPConvergenceError(
                            "IMAP provider Trash "
                            "move failed."
                        )


                    moved_count += 1


        with transaction.atomic():

            current_ids = list(
                InboxMessage.objects
                .select_for_update()
                .filter(
                    conversation=conversation,
                    user=user,
                    organization=(
                        conversation.organization
                    ),
                    email_account=account,
                    platform="imap",
                    is_draft=False,
                )
                .exclude(
                    folder="trash"
                )
                .values_list(
                    "id",
                    flat=True,
                )
                .order_by(
                    "id"
                )
            )


            if (
                set(
                    current_ids
                )
                !=
                set(
                    message_ids
                )
            ):
                raise IMAPConvergenceError(
                    "Conversation changed while "
                    "provider Trash was executing."
                )


            (
                InboxMessage.objects
                .filter(
                    id__in=message_ids
                )
                .update(
                    folder="trash"
                )
            )


            locked_conversation = (
                Conversation.objects
                .select_for_update()
                .get(
                    id=conversation.id
                )
            )


            refresh_conversation_local_state(
                locked_conversation
            )


        invalidate_conversation_cache(
            user.id
        )


        log_event(
            logger,
            "info",
            "imap.trash.conversation_moved",
            account_id=(
                account.id
            ),
            conversation_id=(
                conversation.id
            ),
            local_message_count=(
                len(
                    message_ids
                )
            ),
            provider_move_count=(
                moved_count
            ),
        )


        return {
            "status":
                "completed",

            "updated":
                len(
                    message_ids
                ),

            "moved":
                moved_count,
        }


    finally:

        if mail is not None:
            try:
                mail.logout()
            except Exception:
                pass


        release_sync_lock(
            lock
        )
