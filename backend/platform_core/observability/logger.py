import json
import logging


_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


def get_logger(name):

    return logging.getLogger(name)


def log_event(
    logger,
    level,
    event,
    **fields,
):
    """
    Emit a structured operational event.

    The serialized message is stable JSON while the same structured
    payload is also attached to the LogRecord as ``observability``.

    Callers must only provide operational metadata. Message bodies,
    subjects, credentials, tokens, raw provider responses, and other
    sensitive communication content must not be logged.
    """

    if (
        not isinstance(event, str)
        or not event.strip()
    ):
        raise ValueError(
            "Observability event must be a non-empty string."
        )

    if isinstance(level, str):

        try:
            resolved_level = _LEVELS[
                level.strip().lower()
            ]

        except KeyError as exc:
            raise ValueError(
                f"Unsupported observability log level: {level}"
            ) from exc

    elif isinstance(level, int):
        resolved_level = level

    else:
        raise TypeError(
            "Observability level must be a string or integer."
        )

    payload = {
        "event": event,
    }

    for key, value in fields.items():

        if value is not None:
            payload[key] = value

    message = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )

    logger.log(
        resolved_level,
        message,
        extra={
            "event": event,
            "observability": payload,
        },
    )
