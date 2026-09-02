import hashlib
import json
import re


from django.conf import (
    settings,
)


IDEMPOTENCY_TTL_SECONDS = (
    24
    *
    60
    *
    60
)


DELIVERY_LOCK_TTL_SECONDS = (
    15
    *
    60
)


_KEY_PATTERN = re.compile(
    r"^[A-Za-z0-9._:-]{8,128}$"
)


class OutboundIdempotencyConflict(
    ValueError
):
    pass


class OutboundIdempotencyUnavailable(
    RuntimeError
):
    pass


def resolve_outbound_idempotency_key(
    *,
    request,
    explicit=None,
):
    """
    Resolve a user-generated or server-generated semantic send key.

    The same key represents the same user intent.
    Replaying a request with the same key therefore cannot create
    another provider send.

    Existing internal/test callers that provide no key retain
    backwards compatibility.
    """
    value = (
        explicit
    )


    if not value:

        try:

            value = (
                request.headers.get(
                    "Idempotency-Key"
                )
            )

        except Exception:

            value = None


    if not value:

        try:

            value = (
                request.data.get(
                    "idempotency_key"
                )
            )

        except Exception:

            value = None


    if not value:

        return None


    value = (
        str(
            value
        )
        .strip()
    )


    if not _KEY_PATTERN.fullmatch(
        value
    ):

        raise OutboundIdempotencyConflict(
            "Invalid Idempotency-Key. "
            "Use 8-128 characters containing only "
            "letters, numbers, dot, underscore, colon or hyphen."
        )


    return value


def build_outbound_fingerprint(
    *,
    operation,
    payload,
    attachments=None,
):
    attachment_fingerprints = []


    for item in (
        attachments
        or []
    ):

        content = (
            item.get(
                "content"
            )
            or b""
        )


        if isinstance(
            content,
            str,
        ):

            content = content.encode(
                "utf-8"
            )

        else:

            content = bytes(
                content
            )


        attachment_fingerprints.append(
            {
                "filename":
                    str(
                        item.get(
                            "filename"
                        )
                        or ""
                    ),

                "content_type":
                    str(
                        item.get(
                            "content_type"
                        )
                        or ""
                    ),

                "size":
                    int(
                        item.get(
                            "size"
                        )
                        or
                        len(
                            content
                        )
                    ),

                "sha256":
                    hashlib.sha256(
                        content
                    ).hexdigest(),
            }
        )


    canonical = {
        "operation":
            str(
                operation
            ),

        "payload":
            payload,

        "attachments":
            attachment_fingerprints,
    }


    encoded = json.dumps(
        canonical,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        default=str,
    ).encode(
        "utf-8"
    )


    return hashlib.sha256(
        encoded
    ).hexdigest()


def _redis_client():

    client = getattr(
        settings,
        "REDIS_CLIENT",
        None,
    )


    if client is None:

        raise OutboundIdempotencyUnavailable(
            "Outbound delivery safety store is unavailable."
        )


    return client


def _intent_redis_key(
    *,
    user_id,
    idempotency_key,
):

    return (
        "oneuch:outbound-idempotency:"
        +
        str(
            user_id
        )
        +
        ":"
        +
        idempotency_key
    )


def _message_reverse_key(
    *,
    user_id,
    message_id,
):

    return (
        "oneuch:outbound-idempotency-message:"
        +
        str(
            user_id
        )
        +
        ":"
        +
        str(
            message_id
        )
    )


def _delivery_lock_key(
    *,
    user_id,
    idempotency_key,
):

    return (
        "oneuch:outbound-delivery-lock:"
        +
        str(
            user_id
        )
        +
        ":"
        +
        idempotency_key
    )


def _decode_record(
    raw,
):

    if not raw:

        return None


    try:

        record = json.loads(
            raw
        )

    except Exception as exc:

        raise OutboundIdempotencyUnavailable(
            "Outbound delivery safety record is unreadable."
        ) from exc


    if not isinstance(
        record,
        dict,
    ):

        raise OutboundIdempotencyUnavailable(
            "Outbound delivery safety record is invalid."
        )


    return record


def _get_record(
    *,
    user_id,
    idempotency_key,
):

    client = _redis_client()


    try:

        raw = client.get(
            _intent_redis_key(
                user_id=user_id,
                idempotency_key=(
                    idempotency_key
                ),
            )
        )

    except Exception as exc:

        raise OutboundIdempotencyUnavailable(
            "Outbound delivery safety store could not be read."
        ) from exc


    return _decode_record(
        raw
    )


def _save_record(
    *,
    user_id,
    idempotency_key,
    record,
):

    client = _redis_client()


    try:

        client.set(
            _intent_redis_key(
                user_id=user_id,
                idempotency_key=(
                    idempotency_key
                ),
            ),
            json.dumps(
                record,
                separators=(
                    ",",
                    ":",
                ),
                default=str,
            ),
            ex=(
                IDEMPOTENCY_TTL_SECONDS
            ),
        )

    except Exception as exc:

        raise OutboundIdempotencyUnavailable(
            "Outbound delivery safety store could not be updated."
        ) from exc


def claim_outbound_intent(
    *,
    user_id,
    idempotency_key,
    operation,
    fingerprint,
):

    client = _redis_client()


    redis_key = (
        _intent_redis_key(
            user_id=user_id,
            idempotency_key=(
                idempotency_key
            ),
        )
    )


    record = {
        "version":
            1,

        "user_id":
            user_id,

        "idempotency_key":
            idempotency_key,

        "operation":
            operation,

        "fingerprint":
            fingerprint,

        "state":
            "processing",

        "message_id":
            None,

        "provider_message_id":
            None,

        "http_status":
            None,

        "response_data":
            None,
    }


    try:

        created = client.set(
            redis_key,
            json.dumps(
                record,
                separators=(
                    ",",
                    ":",
                ),
            ),
            nx=True,
            ex=(
                IDEMPOTENCY_TTL_SECONDS
            ),
        )

    except Exception as exc:

        raise OutboundIdempotencyUnavailable(
            "Outbound delivery safety store could not reserve this send."
        ) from exc


    if created:

        return (
            record,
            True,
        )


    existing = (
        _get_record(
            user_id=user_id,
            idempotency_key=(
                idempotency_key
            ),
        )
    )


    if existing is None:

        raise OutboundIdempotencyUnavailable(
            "Outbound delivery safety reservation disappeared."
        )


    if (
        existing.get(
            "operation"
        )
        !=
        operation
        or
        existing.get(
            "fingerprint"
        )
        !=
        fingerprint
    ):

        raise OutboundIdempotencyConflict(
            "This Idempotency-Key was already used "
            "for a different outbound message."
        )


    return (
        existing,
        False,
    )


def bind_outbound_message(
    *,
    user_id,
    idempotency_key,
    message_id,
    response_data=None,
    http_status=None,
):

    record = (
        _get_record(
            user_id=user_id,
            idempotency_key=(
                idempotency_key
            ),
        )
    )


    if record is None:

        raise OutboundIdempotencyUnavailable(
            "Outbound delivery reservation is missing."
        )


    record[
        "message_id"
    ] = message_id


    if response_data is not None:

        record[
            "response_data"
        ] = response_data


    if http_status is not None:

        record[
            "http_status"
        ] = int(
            http_status
        )


    _save_record(
        user_id=user_id,
        idempotency_key=(
            idempotency_key
        ),
        record=record,
    )


    client = _redis_client()


    try:

        client.set(
            _message_reverse_key(
                user_id=user_id,
                message_id=(
                    message_id
                ),
            ),
            idempotency_key,
            ex=(
                IDEMPOTENCY_TTL_SECONDS
            ),
        )

    except Exception as exc:

        raise OutboundIdempotencyUnavailable(
            "Outbound message safety index could not be updated."
        ) from exc


    return record


def complete_outbound_intent(
    *,
    user_id,
    idempotency_key,
    message_id=None,
    provider_message_id=None,
    response_data=None,
    http_status=None,
):

    record = (
        _get_record(
            user_id=user_id,
            idempotency_key=(
                idempotency_key
            ),
        )
    )


    if record is None:

        raise OutboundIdempotencyUnavailable(
            "Outbound delivery reservation is missing."
        )


    if message_id is not None:

        record[
            "message_id"
        ] = message_id


    if provider_message_id is not None:

        record[
            "provider_message_id"
        ] = str(
            provider_message_id
        )


    if response_data is not None:

        record[
            "response_data"
        ] = response_data


    if http_status is not None:

        record[
            "http_status"
        ] = int(
            http_status
        )


    record[
        "state"
    ] = "completed"


    _save_record(
        user_id=user_id,
        idempotency_key=(
            idempotency_key
        ),
        record=record,
    )


    if record.get(
        "message_id"
    ) is not None:

        client = _redis_client()


        try:

            client.set(
                _message_reverse_key(
                    user_id=user_id,
                    message_id=(
                        record[
                            "message_id"
                        ]
                    ),
                ),
                idempotency_key,
                ex=(
                    IDEMPOTENCY_TTL_SECONDS
                ),
            )

        except Exception as exc:

            raise OutboundIdempotencyUnavailable(
                "Outbound message safety index could not be completed."
            ) from exc


    return record




def mark_outbound_intent_uncertain(
    *,
    user_id,
    idempotency_key,
    message_id=None,
    error=None,
):

    record = (
        _get_record(
            user_id=user_id,
            idempotency_key=(
                idempotency_key
            ),
        )
    )


    if record is None:

        raise OutboundIdempotencyUnavailable(
            "Outbound delivery reservation is missing."
        )


    record[
        "state"
    ] = "delivery_uncertain"


    if message_id is not None:

        record[
            "message_id"
        ] = message_id


    record[
        "http_status"
    ] = 409


    record[
        "response_data"
    ] = {
        "status":
            "delivery_uncertain",

        "message_id":
            (
                message_id
                if message_id is not None
                else record.get(
                    "message_id"
                )
            ),

        "error": (
            "Provider delivery outcome is uncertain. "
            "One UCH will not resend this message automatically."
        ),

        "provider_error":
            (
                str(
                    error
                )
                if error
                else None
            ),
    }


    _save_record(
        user_id=user_id,
        idempotency_key=(
            idempotency_key
        ),
        record=record,
    )


    return record



def replay_outbound_intent(
    record,
):

    payload = dict(
        record.get(
            "response_data"
        )
        or {}
    )


    payload[
        "idempotent_replay"
    ] = True


    if record.get(
        "message_id"
    ) is not None:

        payload.setdefault(
            "message_id",
            record[
                "message_id"
            ],
        )


    if (
        record.get(
            "state"
        )
        ==
        "delivery_uncertain"
    ):

        payload.setdefault(
            "status",
            "delivery_uncertain",
        )


        payload.setdefault(
            "error",
            (
                "Provider delivery outcome is uncertain. "
                "One UCH will not resend this message automatically."
            ),
        )


        return (
            payload,
            409,
        )


    if (
        record.get(
            "state"
        )
        ==
        "completed"
    ):

        payload.setdefault(
            "status",
            "sent",
        )


        return (
            payload,
            int(
                record.get(
                    "http_status"
                )
                or 200
            ),
        )


    payload.setdefault(
        "status",
        "send_in_progress",
    )


    return (
        payload,
        int(
            record.get(
                "http_status"
            )
            or 202
        ),
    )


def get_outbound_intent(
    *,
    user_id,
    idempotency_key,
):

    return _get_record(
        user_id=user_id,
        idempotency_key=(
            idempotency_key
        ),
    )


def get_outbound_intent_for_message(
    *,
    user_id,
    message_id,
):

    client = _redis_client()


    try:

        idempotency_key = client.get(
            _message_reverse_key(
                user_id=user_id,
                message_id=(
                    message_id
                ),
            )
        )

    except Exception as exc:

        raise OutboundIdempotencyUnavailable(
            "Outbound message safety index could not be read."
        ) from exc


    if not idempotency_key:

        return None


    return _get_record(
        user_id=user_id,
        idempotency_key=(
            idempotency_key
        ),
    )


def acquire_outbound_delivery_lock(
    *,
    user_id,
    idempotency_key,
):

    client = _redis_client()


    try:

        return bool(
            client.set(
                _delivery_lock_key(
                    user_id=user_id,
                    idempotency_key=(
                        idempotency_key
                    ),
                ),
                "1",
                nx=True,
                ex=(
                    DELIVERY_LOCK_TTL_SECONDS
                ),
            )
        )

    except Exception as exc:

        raise OutboundIdempotencyUnavailable(
            "Outbound provider delivery lock is unavailable."
        ) from exc


def release_outbound_delivery_lock(
    *,
    user_id,
    idempotency_key,
):

    try:

        _redis_client().delete(
            _delivery_lock_key(
                user_id=user_id,
                idempotency_key=(
                    idempotency_key
                ),
            )
        )

    except Exception:

        # The semantic intent remains authoritative even if a
        # best-effort short delivery lock cannot be removed.
        pass


def abandon_outbound_intent(
    *,
    user_id,
    idempotency_key,
    message_id=None,
):
    """
    Use only before any provider delivery has started.
    """
    client = _redis_client()


    keys = [
        _intent_redis_key(
            user_id=user_id,
            idempotency_key=(
                idempotency_key
            ),
        )
    ]


    if message_id is not None:

        keys.append(
            _message_reverse_key(
                user_id=user_id,
                message_id=(
                    message_id
                ),
            )
        )


    try:

        client.delete(
            *keys
        )

    except Exception:

        pass
