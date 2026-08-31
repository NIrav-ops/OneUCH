import ast
import json
import logging
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

from platform_core.observability.logger import (
    get_logger,
    log_event,
)


class _CaptureHandler(logging.Handler):

    def __init__(self):

        super().__init__()

        self.records = []

    def emit(self, record):

        self.records.append(
            record
        )


class ObservabilityContractTests(
    SimpleTestCase
):

    def test_runtime_observability_contract(self):

        logger = get_logger(
            "oneuch.runtime.contract_test"
        )

        old_handlers = list(
            logger.handlers
        )

        old_level = logger.level
        old_propagate = logger.propagate
        old_disabled = logger.disabled

        handler = _CaptureHandler()

        try:

            logger.handlers = [
                handler,
            ]

            logger.setLevel(
                logging.DEBUG
            )

            logger.propagate = False
            logger.disabled = False

            log_event(
                logger,
                "info",
                "sync.account.started",
                provider="gmail",
                account_id=17,
                omitted=None,
            )

        finally:

            logger.handlers = (
                old_handlers
            )

            logger.setLevel(
                old_level
            )

            logger.propagate = (
                old_propagate
            )

            logger.disabled = (
                old_disabled
            )

        self.assertEqual(
            len(handler.records),
            1,
        )

        record = handler.records[0]

        payload = json.loads(
            record.getMessage()
        )

        self.assertEqual(
            payload,
            {
                "account_id": 17,
                "event": (
                    "sync.account.started"
                ),
                "provider": "gmail",
            },
        )

        self.assertEqual(
            record.event,
            "sync.account.started",
        )

        self.assertEqual(
            record.observability,
            payload,
        )

        logging_config = (
            settings.LOGGING
        )

        self.assertIn(
            "request_context",
            logging_config["filters"],
        )

        self.assertEqual(
            logging_config[
                "handlers"
            ][
                "console"
            ][
                "filters"
            ],
            [
                "request_context",
            ],
        )

        self.assertIn(
            "oneuch.runtime",
            logging_config[
                "loggers"
            ],
        )

        source_root = Path(
            settings.BASE_DIR
        )

        connector_files = (
            (
                source_root
                / "googleapis"
                / "services"
                / "gmail_sync.py"
            ),
            (
                source_root
                / "microsoftapis"
                / "services"
                / "outlook_sync.py"
            ),
            (
                source_root
                / "inbox"
                / "tasks.py"
            ),
        )

        for source_file in (
            connector_files
        ):

            source = (
                source_file
                .read_text(
                    encoding="utf-8"
                )
            )

            tree = ast.parse(
                source,
                filename=str(
                    source_file
                ),
            )

            raw_print_lines = [
                node.lineno
                for node in ast.walk(
                    tree
                )
                if (
                    isinstance(
                        node,
                        ast.Call,
                    )
                    and isinstance(
                        node.func,
                        ast.Name,
                    )
                    and node.func.id
                    == "print"
                )
            ]

            self.assertEqual(
                raw_print_lines,
                [],
                (
                    "Raw print() remains "
                    f"in {source_file}: "
                    f"{raw_print_lines}"
                ),
            )
