from email.utils import (
    formataddr,
    getaddresses,
)

from django.core.exceptions import (
    ValidationError,
)

from django.core.validators import (
    validate_email,
)


RECIPIENT_BUCKETS = (
    "to",
    "cc",
    "bcc",
)


def _normalize_name(
    value,
):
    return " ".join(
        str(
            value
            or ""
        ).split()
    )[:255]


def _normalize_email(
    value,
):
    email = (
        str(
            value
            or ""
        )
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


def _identity(
    *,
    name="",
    email="",
):
    normalized_email = (
        _normalize_email(
            email
        )
    )

    if not normalized_email:
        return None

    return {
        "name":
            _normalize_name(
                name
            ),

        "email":
            normalized_email,
    }


def parse_recipient_field(
    value,
):
    """
    Accept both legacy strings and the structured recipient
    arrays emitted by the P2 chip UI.
    """

    if value is None:
        return []


    if isinstance(
        value,
        dict,
    ):
        source_values = [
            value
        ]

    elif isinstance(
        value,
        (
            list,
            tuple,
        ),
    ):
        source_values = list(
            value
        )

    else:
        source_values = [
            value
        ]


    identities = []

    seen = set()


    for source in source_values:

        parsed = []


        if isinstance(
            source,
            dict,
        ):

            candidate = (
                _identity(
                    name=(
                        source.get(
                            "name",
                            ""
                        )
                    ),
                    email=(
                        source.get(
                            "email"
                        )
                        or
                        source.get(
                            "address"
                        )
                    ),
                )
            )

            if candidate:
                parsed.append(
                    candidate
                )


        else:

            text = (
                str(
                    source
                    or ""
                )
                .replace(
                    ";",
                    ",",
                )
            )


            for name, address in (
                getaddresses(
                    [
                        text
                    ]
                )
            ):

                candidate = (
                    _identity(
                        name=name,
                        email=address,
                    )
                )

                if candidate:
                    parsed.append(
                        candidate
                    )


        for candidate in parsed:

            email = candidate[
                "email"
            ]

            if email in seen:
                continue

            seen.add(
                email
            )

            identities.append(
                candidate
            )


    return identities


def normalize_recipient_buckets(
    *,
    to=None,
    cc=None,
    bcc=None,
    require_to=True,
):
    """
    Normalize and de-duplicate recipient roles.

    Role priority is To -> CC -> BCC. If the same address was
    accidentally entered more than once, it is retained only
    in the highest-priority role.
    """

    parsed = {
        "to":
            parse_recipient_field(
                to
            ),

        "cc":
            parse_recipient_field(
                cc
            ),

        "bcc":
            parse_recipient_field(
                bcc
            ),
    }


    seen = set()

    normalized = {
        "to": [],
        "cc": [],
        "bcc": [],
        "reply_to": [],
    }


    for bucket in RECIPIENT_BUCKETS:

        for identity in (
            parsed[
                bucket
            ]
        ):

            email = identity[
                "email"
            ]

            if email in seen:
                continue

            seen.add(
                email
            )

            normalized[
                bucket
            ].append(
                identity
            )


    if (
        require_to
        and
        not normalized[
            "to"
        ]
    ):
        raise ValueError(
            "Recipient required"
        )


    flat_addresses = []

    for bucket in RECIPIENT_BUCKETS:

        for identity in (
            normalized[
                bucket
            ]
        ):
            flat_addresses.append(
                identity[
                    "email"
                ]
            )


    return (
        normalized,
        ", ".join(
            flat_addresses
        ),
    )


def mime_recipient_header(
    identities,
):
    values = []

    for identity in (
        identities
        or []
    ):

        name = identity.get(
            "name",
            "",
        )

        email = identity.get(
            "email",
            "",
        )

        if not email:
            continue


        values.append(
            formataddr(
                (
                    name,
                    email,
                )
            )
            if name
            else email
        )


    return ", ".join(
        values
    )


def graph_recipient_payload(
    identities,
):
    result = []

    for identity in (
        identities
        or []
    ):

        email = identity.get(
            "email",
            "",
        )

        if not email:
            continue


        email_address = {
            "address":
                email
        }


        name = identity.get(
            "name",
            "",
        )

        if name:
            email_address[
                "name"
            ] = name


        result.append(
            {
                "emailAddress":
                    email_address
            }
        )


    return result
