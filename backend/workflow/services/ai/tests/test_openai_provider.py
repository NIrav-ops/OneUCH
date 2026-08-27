import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from workflow.services.ai.contracts import (
    AIRequest,
)
from workflow.services.ai.providers.openai import (
    OpenAIProvider,
)


class OpenAIProviderTests(
    SimpleTestCase
):

    def test_missing_api_key_fails_cleanly(
        self,
    ):
        provider = OpenAIProvider(
            api_key="",
        )

        with patch.dict(
            "os.environ",
            {},
            clear=True,
        ):
            provider.api_key = None

            with self.assertRaises(
                RuntimeError
            ):
                provider._build_client()

    @patch(
        "workflow.services.ai.providers."
        "openai.OpenAIProvider._build_client"
    )
    def test_action_list_is_normalized(
        self,
        build_client_mock,
    ):
        response = SimpleNamespace(
            id="resp_test_001",
            output_text=json.dumps(
                {
                    "actions": [
                        {
                            "title":
                                "Coordinate with finance",
                            "description":
                                "Resolve the issue.",
                            "priority": 80,
                            "confidence": 0.95,
                            "metadata": {
                                "evidence":
                                    "coordinate with finance"
                            },
                        }
                    ]
                }
            ),
            usage=SimpleNamespace(
                input_tokens=100,
                output_tokens=40,
                total_tokens=140,
            ),
        )

        client = Mock()
        client.responses.create.return_value = (
            response
        )

        build_client_mock.return_value = (
            client
        )

        provider = OpenAIProvider(
            api_key="test-key",
        )

        result = provider.execute(
            AIRequest(
                prompt=(
                    "Extract Actions."
                ),
                system_prompt=(
                    "You are an extractor."
                ),
                response_type=(
                    "action_list"
                ),
                model=(
                    "gpt-5.6-luna"
                ),
            )
        )

        self.assertTrue(
            result.success
        )

        self.assertEqual(
            result.provider,
            "openai",
        )

        self.assertEqual(
            result.model,
            "gpt-5.6-luna",
        )

        self.assertEqual(
            result.total_tokens,
            140,
        )

        self.assertEqual(
            result.output[
                "actions"
            ][0]["title"],
            "Coordinate with finance",
        )

    @patch(
        "workflow.services.ai.providers."
        "openai.OpenAIProvider._build_client"
    )
    def test_invalid_json_raises(
        self,
        build_client_mock,
    ):
        response = SimpleNamespace(
            id="resp_test_002",
            output_text=(
                "not-json"
            ),
            usage=None,
        )

        client = Mock()
        client.responses.create.return_value = (
            response
        )

        build_client_mock.return_value = (
            client
        )

        provider = OpenAIProvider(
            api_key="test-key",
        )

        with self.assertRaises(
            ValueError
        ):
            provider.execute(
                AIRequest(
                    prompt="Extract Actions.",
                    response_type=(
                        "action_list"
                    ),
                )
            )

    @patch(
        "workflow.services.ai.providers."
        "openai.OpenAIProvider._build_client"
    )
    def test_gpt_5_6_omits_temperature(
        self,
        build_client_mock,
    ):
        response = SimpleNamespace(
            id="resp_test_temperature",
            output_text="ONEUCH_OK",
            usage=SimpleNamespace(
                input_tokens=10,
                output_tokens=2,
                total_tokens=12,
            ),
        )

        client = Mock()
        client.responses.create.return_value = response
        build_client_mock.return_value = client

        provider = OpenAIProvider(
            api_key="test-key",
        )

        result = provider.execute(
            AIRequest(
                prompt="Return ONEUCH_OK.",
                response_type="text",
                model="gpt-5.6-luna",
                temperature=0.0,
                max_tokens=100,
            )
        )

        self.assertTrue(result.success)

        kwargs = (
            client.responses.create
            .call_args.kwargs
        )

        self.assertEqual(
            kwargs["model"],
            "gpt-5.6-luna",
        )

        self.assertNotIn(
            "temperature",
            kwargs,
        )

    @patch(
        "workflow.services.ai.providers."
        "openai.OpenAIProvider._build_client"
    )
    def test_response_schema_uses_structured_outputs(
        self,
        build_client_mock,
    ):
        response = SimpleNamespace(
            id="resp_structured_001",
            output_text=json.dumps(
                {
                    "actions": [],
                }
            ),
            usage=SimpleNamespace(
                input_tokens=20,
                output_tokens=5,
                total_tokens=25,
            ),
        )

        client = Mock()

        client.responses.create.return_value = (
            response
        )

        build_client_mock.return_value = (
            client
        )

        provider = OpenAIProvider(
            api_key="test-key",
        )

        schema = {
            "type": "object",
            "required": [
                "actions",
            ],
            "additionalProperties": False,
            "properties": {
                "actions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                    },
                },
            },
        }

        result = provider.execute(
            AIRequest(
                prompt="Extract actions.",
                response_type="action_list",
                response_schema=schema,
                model="gpt-5.6-luna",
                max_tokens=200,
            )
        )

        self.assertTrue(
            result.success
        )

        kwargs = (
            client.responses.create
            .call_args.kwargs
        )

        self.assertIn(
            "text",
            kwargs,
        )

        structured_format = (
            kwargs[
                "text"
            ][
                "format"
            ]
        )

        self.assertEqual(
            structured_format["type"],
            "json_schema",
        )

        self.assertEqual(
            structured_format["name"],
            "oneuch_action_list",
        )

        self.assertTrue(
            structured_format["strict"]
        )

        self.assertEqual(
            structured_format["schema"],
            schema,
        )

