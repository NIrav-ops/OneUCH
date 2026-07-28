from django.test import TestCase

from platform_core.configuration.defaults import (
    load_defaults,
)

from platform_core.configuration.manager import (
    ConfigurationManager,
)

from platform_core.configuration.repository import (
    ConfigurationRepository,
)


class ConfigurationTests(TestCase):

    def tearDown(self):

        ConfigurationRepository.clear()

    def test_defaults_loaded(self):

        load_defaults()

        self.assertEqual(

            ConfigurationManager.get(

                "AI_PROVIDER",

            ),

            "OpenAI",

        )

    def test_scheduler_enabled(self):

        load_defaults()

        self.assertTrue(

            ConfigurationManager.get(

                "SCHEDULER_ENABLED",

            )

        )

    def test_custom_setting(self):

        ConfigurationManager.set(

            "TIMEOUT",

            30,

        )

        self.assertEqual(

            ConfigurationManager.get(

                "TIMEOUT",

            ),

            30,

        )

    def test_unknown(self):

        self.assertIsNone(

            ConfigurationManager.get(

                "UNKNOWN",

            )

        )