from email.utils import (
    getaddresses,
)

from django.core.exceptions import (
    ValidationError,
)

from django.core.validators import (
    validate_email,
)

from django.db import (
    transaction,
)

from django.db.models import (
    Q,
)

from django.utils import (
    timezone,
)

from email_accounts.models import (
    EmailAccount,
)

from inbox.models import (
    InboxMessage,
    OrganizationUser,
    RecipientContact,
    RecipientDirectoryState,
)


SUPPORTED_PLATFORMS = (
    "gmail",
    "outlook",
)

DEFAULT_BATCH_SIZE = 250

MAX_BATCH_SIZE = 1000

DEFAULT_SUGGESTION_LIMIT = 10

MAX_SUGGESTION_LIMIT = 20

MAX_SEARCH_CANDIDATES = 500


class RecipientDirectoryUnavailable(
    RuntimeError
):
    pass


def _organization_for_user(
    user,
):
    membership = (
        OrganizationUser.objects
        .select_related(
            "organization"
        )
        .filter(
            user=user,
            organization__is_active=True,
        )
        .first()
    )

    if membership is None:
        raise RecipientDirectoryUnavailable(
            "Active organization membership required."
        )

    return membership.organization


def _normalize_name(
    value,
):
    if value is None:
        return ""

    return " ".join(
        str(value).split()
    )[:255]


def _normalize_email(
    value,
):
    if value is None:
        return None

    email = (
        str(value)
        .strip()
        .strip("<>")
        .lower()
    )

    if not email:
        return None

    try:
        validate_email(
            email
        )
    except ValidationError:
        return None

    return email


def _identity_from_dict(
    value,
):
    if not isinstance(
        value,
        dict,
    ):
        return None

    email = _normalize_email(
        value.get(
            "email"
        )
        or
        value.get(
            "address"
        )
    )

    if not email:
        return None

    return {
        "email":
            email,

        "name":
            _normalize_name(
                value.get(
                    "name"
                )
            ),
    }


def _identities_from_flat(
    value,
):
    source = (
        str(
            value
            or ""
        )
        .replace(
            ";",
            ",",
        )
    )

    identities = []

    for name, address in getaddresses(
        [
            source
        ]
    ):
        email = _normalize_email(
            address
        )

        if not email:
            continue

        identities.append(
            {
                "email":
                    email,

                "name":
                    _normalize_name(
                        name
                    ),
            }
        )

    return identities


def _self_addresses(
    user,
):
    addresses = set()

    user_email = _normalize_email(
        getattr(
            user,
            "email",
            "",
        )
    )

    if user_email:
        addresses.add(
            user_email
        )

    for address in (
        EmailAccount.objects
        .filter(
            user=user
        )
        .values_list(
            "email_address",
            flat=True,
        )
    ):
        normalized = _normalize_email(
            address
        )

        if normalized:
            addresses.add(
                normalized
            )

    return addresses


def _message_contact_events(
    *,
    message,
    self_addresses,
):
    """
    Build one contact event per unique external email address
    for this message.

    message_count is therefore incremented at most once per
    contact per InboxMessage, while role counters can record
    multiple roles on the same message.
    """

    events = {}


    def add_identity(
        identity,
        role,
    ):
        if not identity:
            return

        email = identity[
            "email"
        ]

        if email in self_addresses:
            return

        event = events.setdefault(
            email,
            {
                "email":
                    email,

                "name":
                    "",

                "roles":
                    set(),
            },
        )

        name = (
            identity.get(
                "name"
            )
            or ""
        )

        if name:
            event[
                "name"
            ] = name

        event[
            "roles"
        ].add(
            role
        )


    sender_meta = (
        message.sender_meta
        if isinstance(
            message.sender_meta,
            dict,
        )
        else {}
    )

    sender_identity = (
        _identity_from_dict(
            sender_meta
        )
    )

    if sender_identity is None:
        fallback_sender = (
            _identities_from_flat(
                message.sender
            )
        )

        if fallback_sender:
            sender_identity = (
                fallback_sender[
                    0
                ]
            )

    add_identity(
        sender_identity,
        "from",
    )


    recipient_meta = (
        message.recipient_meta
        if isinstance(
            message.recipient_meta,
            dict,
        )
        else {}
    )


    structured_recipient_found = (
        False
    )


    for bucket in (
        "to",
        "cc",
        "bcc",
        "reply_to",
    ):
        values = recipient_meta.get(
            bucket,
            []
        )

        if not isinstance(
            values,
            list,
        ):
            continue

        for value in values:
            identity = (
                _identity_from_dict(
                    value
                )
            )

            if identity is None:
                continue

            structured_recipient_found = (
                True
            )

            add_identity(
                identity,
                bucket,
            )


    # Older pre-P1 records may only have the historical flat
    # recipients field. Preserve their usefulness for P2
    # without pretending that legacy flat data can distinguish
    # CC/BCC.
    if (
        not structured_recipient_found
        and
        message.recipients
    ):
        for identity in (
            _identities_from_flat(
                message.recipients
            )
        ):
            add_identity(
                identity,
                "to",
            )


    return events


def _apply_message_to_directory(
    *,
    user,
    organization,
    message,
    self_addresses,
):
    events = (
        _message_contact_events(
            message=message,
            self_addresses=(
                self_addresses
            ),
        )
    )

    seen_at = (
        message.received_at
        or
        message.created_at
        or
        timezone.now()
    )


    for event in events.values():
        email = event[
            "email"
        ]

        roles = event[
            "roles"
        ]

        defaults = {
            "email":
                email,

            "display_name":
                event[
                    "name"
                ],

            "first_seen_at":
                seen_at,

            "last_seen_at":
                seen_at,
        }


        contact, created = (
            RecipientContact.objects
            .get_or_create(
                user=user,
                organization=(
                    organization
                ),
                normalized_email=(
                    email
                ),
                defaults=defaults,
            )
        )


        if not created:
            if (
                seen_at
                <
                contact.first_seen_at
            ):
                contact.first_seen_at = (
                    seen_at
                )

            if (
                seen_at
                >=
                contact.last_seen_at
            ):
                contact.last_seen_at = (
                    seen_at
                )

                if event[
                    "name"
                ]:
                    contact.display_name = (
                        event[
                            "name"
                        ]
                    )

            contact.email = (
                email
            )


        contact.message_count += 1


        if (
            message.direction
            ==
            "outbound"
            and
            roles.intersection(
                {
                    "to",
                    "cc",
                    "bcc",
                }
            )
        ):
            contact.sent_count += 1


        if (
            message.direction
            ==
            "inbound"
            and
            "from"
            in roles
        ):
            contact.received_count += 1


        if "to" in roles:
            contact.to_count += 1

        if "cc" in roles:
            contact.cc_count += 1

        if "bcc" in roles:
            contact.bcc_count += 1

        if "reply_to" in roles:
            contact.reply_to_count += 1


        contact.save()


def refresh_recipient_directory(
    *,
    user,
    batch_size=DEFAULT_BATCH_SIZE,
):
    """
    Incrementally materialize recipient intelligence.

    The directory state watermark advances in the same database
    transaction as contact counters, so repeating after a
    failure cannot double-count a committed message.
    """

    organization = (
        _organization_for_user(
            user
        )
    )

    try:
        requested_batch = int(
            batch_size
        )
    except (
        TypeError,
        ValueError,
    ):
        requested_batch = (
            DEFAULT_BATCH_SIZE
        )

    batch_size = max(
        1,
        min(
            requested_batch,
            MAX_BATCH_SIZE,
        ),
    )


    state, _ = (
        RecipientDirectoryState.objects
        .get_or_create(
            user=user,
            organization=(
                organization
            ),
        )
    )


    self_addresses = (
        _self_addresses(
            user
        )
    )


    processed_count = 0


    while True:
        with transaction.atomic():
            locked_state = (
                RecipientDirectoryState.objects
                .select_for_update()
                .get(
                    pk=state.pk
                )
            )


            batch = list(
                InboxMessage.objects
                .filter(
                    user=user,
                    organization=(
                        organization
                    ),
                    is_draft=False,
                    platform__in=(
                        SUPPORTED_PLATFORMS
                    ),
                    id__gt=(
                        locked_state
                        .last_indexed_message_id
                    ),
                )
                .order_by(
                    "id"
                )
                .only(
                    "id",
                    "user_id",
                    "organization_id",
                    "platform",
                    "direction",
                    "sender",
                    "recipients",
                    "sender_meta",
                    "recipient_meta",
                    "received_at",
                    "created_at",
                )[
                    :batch_size
                ]
            )


            if not batch:
                state = (
                    locked_state
                )

                break


            for message in batch:
                _apply_message_to_directory(
                    user=user,
                    organization=(
                        organization
                    ),
                    message=message,
                    self_addresses=(
                        self_addresses
                    ),
                )


            locked_state.last_indexed_message_id = (
                batch[
                    -1
                ].id
            )

            locked_state.indexed_message_count += (
                len(
                    batch
                )
            )

            locked_state.last_indexed_at = (
                timezone.now()
            )

            locked_state.save(
                update_fields=[
                    "last_indexed_message_id",
                    "indexed_message_count",
                    "last_indexed_at",
                    "updated_at",
                ]
            )


            processed_count += (
                len(
                    batch
                )
            )

            state = (
                locked_state
            )


    return (
        state,
        processed_count,
    )


def _match_rank(
    *,
    contact,
    query,
):
    if not query:
        return 0

    email = (
        contact
        .normalized_email
        .lower()
    )

    name = (
        contact
        .display_name
        .lower()
    )


    if email == query:
        return 6

    if name == query:
        return 5

    if email.startswith(
        query
    ):
        return 4

    if name.startswith(
        query
    ):
        return 3

    if query in email:
        return 2

    if query in name:
        return 1

    return 0


def _ranking_key(
    *,
    contact,
    query,
):
    return (
        _match_rank(
            contact=contact,
            query=query,
        ),

        contact.sent_count,

        contact.message_count,

        contact.received_count,

        contact.last_seen_at.timestamp(),
    )


def suggest_recipients(
    *,
    user,
    query="",
    limit=DEFAULT_SUGGESTION_LIMIT,
    refresh=True,
):
    organization = (
        _organization_for_user(
            user
        )
    )

    query = (
        str(
            query
            or ""
        )
        .strip()
        .lower()[
            :254
        ]
    )


    try:
        requested_limit = int(
            limit
        )
    except (
        TypeError,
        ValueError,
    ):
        requested_limit = (
            DEFAULT_SUGGESTION_LIMIT
        )


    limit = max(
        1,
        min(
            requested_limit,
            MAX_SUGGESTION_LIMIT,
        ),
    )


    if refresh:
        state, refreshed_count = (
            refresh_recipient_directory(
                user=user
            )
        )

    else:
        state = (
            RecipientDirectoryState.objects
            .filter(
                user=user,
                organization=(
                    organization
                ),
            )
            .first()
        )

        refreshed_count = 0


    contacts = (
        RecipientContact.objects
        .filter(
            user=user,
            organization=(
                organization
            ),
        )
    )


    if query:
        contacts = (
            contacts.filter(
                Q(
                    normalized_email__icontains=(
                        query
                    )
                )
                |
                Q(
                    display_name__icontains=(
                        query
                    )
                )
            )
        )


    candidates = list(
        contacts[
            :MAX_SEARCH_CANDIDATES
        ]
    )


    candidates.sort(
        key=lambda contact: (
            _ranking_key(
                contact=contact,
                query=query,
            )
        ),
        reverse=True,
    )


    results = []


    for contact in candidates[
        :limit
    ]:
        results.append(
            {
                "id":
                    contact.id,

                "email":
                    contact.email,

                "name":
                    contact.display_name,

                "message_count":
                    contact.message_count,

                "sent_count":
                    contact.sent_count,

                "received_count":
                    contact.received_count,

                "last_seen_at":
                    contact.last_seen_at,
            }
        )


    return {
        "results":
            results,

        "indexed_message_count":
            (
                state.indexed_message_count
                if state
                else 0
            ),

        "refreshed_message_count":
            refreshed_count,
    }
