"""
Enterprise Knowledge Logger

Single logging entry point for the
Knowledge Engine.
"""

import logging


logger = logging.getLogger("knowledge")


def log_info(message, **context):

    logger.info(
        "%s | %s",
        message,
        context,
    )


def log_warning(message, **context):

    logger.warning(
        "%s | %s",
        message,
        context,
    )


def log_error(message, **context):

    logger.exception(
        "%s | %s",
        message,
        context,
    )