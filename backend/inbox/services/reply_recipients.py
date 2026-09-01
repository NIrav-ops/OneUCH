from email_accounts.models import (
    EmailAccount,
)

from inbox.services.recipient_payload import (
    normalize_recipient_buckets,
    parse_recipient_field,
)


VALID_REPLY_MODES = {
    "reply",
    "reply_all",
}


class ReplyRecipientError(
    ValueError
):
    pass


def _self_addresses(
    user,
):
    addresses = {
        str(
            value
            or ""
        )
        .strip()
        .lower()

        for value in (
            EmailAccount.objects
            .filter(
                user=user
            )
            .values_list(
                "email_address",
                flat=True,
            )
        )

        if value
    }


    if getattr(
        user,
        "email",
        None,
    ):
        addresses.add(
            str(
                user.email
            )
            .strip()
            .lower()
        )


    return addresses


def _structured_bucket(
    message,
    bucket,
):
    meta = (
        message.recipient_meta
        if isinstance(
            message.recipient_meta,
            dict,
        )
        else {}
    )


    return parse_recipient_field(
        meta.get(
            bucket,
            [],
        )
    )


def _sender_identities(
    message,
):
    sender_meta = (
        message.sender_meta
        if isinstance(
            message.sender_meta,
            dict,
        )
        else {}
    )


    identities = (
        parse_recipient_field(
            sender_meta
        )
    )


    if identities:
        return identities


    return parse_recipient_field(
        message.sender
    )


def _without_self(
    identities,
    *,
    self_addresses,
):
    return [
        identity
        for identity
        in identities
        if (
            identity.get(
                "email"
            )
            not in self_addresses
        )
    ]


def resolve_reply_recipients(
    *,
    message,
    user,
    mode="reply",
):
    """
    Governed reply-recipient resolution.

    Inbound:
      Reply     -> Reply-To, otherwise sender.
      Reply All -> Reply-To/sender + original To/Cc,
                   excluding every mailbox owned by the user.

    Outbound:
      Reply     -> first original To recipient.
      Reply All -> original To + Cc recipients.

    Bcc is intentionally never propagated into Reply All.
    """

    if mode not in VALID_REPLY_MODES:
        raise ReplyRecipientError(
            "Unsupported reply mode."
        )


    self_addresses = (
        _self_addresses(
            user
        )
    )


    to_bucket = (
        _structured_bucket(
            message,
            "to",
        )
    )

    cc_bucket = (
        _structured_bucket(
            message,
            "cc",
        )
    )

    reply_to_bucket = (
        _structured_bucket(
            message,
            "reply_to",
        )
    )


    if message.direction == "inbound":

        primary = (
            reply_to_bucket
            or
            _sender_identities(
                message
            )
        )


        primary = (
            _without_self(
                primary,
                self_addresses=(
                    self_addresses
                ),
            )
        )


        if mode == "reply":

            reply_to = (
                primary
            )

            reply_cc = []


        else:

            reply_to = (
                primary
            )


            reply_cc = (
                _without_self(
                    (
                        to_bucket
                        +
                        cc_bucket
                    ),
                    self_addresses=(
                        self_addresses
                    ),
                )
            )


    else:

        outbound_to = (
            _without_self(
                to_bucket,
                self_addresses=(
                    self_addresses
                ),
            )
        )


        if not outbound_to:

            outbound_to = (
                _without_self(
                    parse_recipient_field(
                        message.recipients
                    ),
                    self_addresses=(
                        self_addresses
                    ),
                )
            )


        if mode == "reply":

            reply_to = (
                outbound_to[
                    :1
                ]
            )

            reply_cc = []


        else:

            reply_to = (
                outbound_to
            )

            reply_cc = (
                _without_self(
                    cc_bucket,
                    self_addresses=(
                        self_addresses
                    ),
                )
            )


    try:

        (
            recipient_meta,
            recipients_flat,
        ) = (
            normalize_recipient_buckets(
                to=reply_to,
                cc=reply_cc,
                bcc=[],
                require_to=True,
            )
        )

    except ValueError as exc:

        raise ReplyRecipientError(
            "No valid reply recipient found."
        ) from exc


    return (
        recipient_meta,
        recipients_flat,
    )
