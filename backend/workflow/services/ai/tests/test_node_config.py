from django.test import SimpleTestCase

from workflow.services.ai.node_config import (
    AINodeConfiguration,
)

from workflow.services.ai.exceptions import (
    AIValidationError,
)


class AINodeConfigurationTests(
    SimpleTestCase
):

    def test_defaults(self):

        config = (
            AINodeConfiguration.from_dict(
                {},
                default_prompt="Process node",
            )
        )

        self.assertEqual(
            config.prompt,
            "Process node",
        )

        self.assertEqual(
            config.provider,
            "mock",
        )

        self.assertEqual(
            config.temperature,
            0.0,
        )

        self.assertEqual(
            config.max_tokens,
            1000,
        )

        self.assertEqual(
            config.response_type,
            "text",
        )

        self.assertTrue(
            config.fail_on_error
        )

        self.assertTrue(
            config.include_runtime_context
        )

    def test_custom_configuration(self):

        config = (
            AINodeConfiguration.from_dict(
                {
                    "prompt":
                        "Summarize communication",

                    "provider":
                        "mock",

                    "model":
                        "enterprise-model",

                    "temperature":
                        0.3,

                    "max_tokens":
                        500,

                    "response_type":
                        "summary",

                    "fail_on_error":
                        False,

                    "include_runtime_context":
                        False,
                },
                default_prompt=(
                    "Default"
                ),
            )
        )

        self.assertEqual(
            config.prompt,
            "Summarize communication",
        )

        self.assertEqual(
            config.model,
            "enterprise-model",
        )

        self.assertEqual(
            config.response_type,
            "summary",
        )

        self.assertFalse(
            config.fail_on_error
        )

        self.assertFalse(
            config.include_runtime_context
        )

    def test_invalid_configuration_type(
        self,
    ):

        with self.assertRaises(
            AIValidationError
        ):
            AINodeConfiguration.from_dict(
                "invalid",
                default_prompt="Test",
            )

    def test_empty_prompt_rejected(self):

        with self.assertRaises(
            AIValidationError
        ):
            AINodeConfiguration.from_dict(
                {
                    "prompt": "   ",
                },
                default_prompt="Test",
            )

    def test_invalid_temperature_rejected(
        self,
    ):

        with self.assertRaises(
            AIValidationError
        ):
            AINodeConfiguration.from_dict(
                {
                    "temperature": 3,
                },
                default_prompt="Test",
            )

    def test_invalid_max_tokens_rejected(
        self,
    ):

        with self.assertRaises(
            AIValidationError
        ):
            AINodeConfiguration.from_dict(
                {
                    "max_tokens": 0,
                },
                default_prompt="Test",
            )

    def test_invalid_fail_on_error_rejected(
        self,
    ):

        with self.assertRaises(
            AIValidationError
        ):
            AINodeConfiguration.from_dict(
                {
                    "fail_on_error":
                        "yes",
                },
                default_prompt="Test",
            )

    def test_invalid_runtime_flag_rejected(
        self,
    ):

        with self.assertRaises(
            AIValidationError
        ):
            AINodeConfiguration.from_dict(
                {
                    "include_runtime_context":
                        1,
                },
                default_prompt="Test",
            )