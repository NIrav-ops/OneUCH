import logging

from django.test import TestCase

from platform_core.observability import get_logger


class LoggingTests(TestCase):

    def test_logger(self):

        logger = get_logger(__name__)

        self.assertIsInstance(
            logger,
            logging.Logger,
        )

    def test_logging_without_request(self):

        logger = get_logger(__name__)

        logger.info(
            "Platform logging test"
        )

        self.assertTrue(True)