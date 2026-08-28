import json
from unittest.mock import (
    Mock,
    patch,
)

from django.test import (
    SimpleTestCase,
)

from workflow.services.ai.contracts import (
    AIRequest,
)
from workflow.services.ai.provider_router import (
    AIProviderRouter,
)
from workflow.services.ai.providers.ollama import (
    OllamaProvider,
)


class OllamaProviderTests(
    SimpleTestCase
):

    def test_router_resolves_ollama(
        self,
    ):
        provider = (
            AIProviderRouter.get_provider(
                "ollama"
            )
        )

        self.assertIsInstance(
            provider,
            OllamaProvider,
        )

    @patch(
        "workflow.services.ai.providers."
        "ollama.requests.post"
    )
    def test_structured_action_response_is_normalized(
        self,
        post_mock,
    ):
        response = Mock()

        response.raise_for_status.return_value = (
            None
        )

        response.json.return_value = {
            "model":
                "local-test-model",

            "message": {
                "role": "assistant",
                "content": json.dumps(
                    {
                        "actions": []
                    }
                ),
            },

            "done": True,
            "done_reason": "stop",

            "prompt_eval_count": 25,
            "eval_count": 5,
        }

        post_mock.return_value = response

        schema = {
            "type": "object",
            "required": [
                "actions",
            ],
            "additionalProperties":
                False,
            "properties": {
                "actions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                    },
                },
            },
        }

        provider = OllamaProvider(
            base_url=(
                "http://127.0.0.1:11434"
            ),
            timeout=10,
        )

        result = provider.execute(
            AIRequest(
                prompt="Extract actions.",
                system_prompt=(
                    "You are an extractor."
                ),
                response_type=(
                    "action_list"
                ),
                response_schema=schema,
                model="local-test-model",
                temperature=0.0,
                max_tokens=200,
            )
        )

        self.assertTrue(
            result.success
        )

        self.assertEqual(
            result.provider,
            "ollama",
        )

        self.assertEqual(
            result.output,
            {
                "actions": []
            },
        )

        self.assertEqual(
            result.prompt_tokens,
            25,
        )

        self.assertEqual(
            result.completion_tokens,
            5,
        )

        self.assertEqual(
            result.total_tokens,
            30,
        )

        post_mock.assert_called_once()

        url = (
            post_mock.call_args.args[0]
        )

        kwargs = (
            post_mock.call_args.kwargs
        )

        self.assertEqual(
            url,
            (
                "http://127.0.0.1:11434"
                "/api/chat"
            ),
        )

        payload = kwargs["json"]

        self.assertFalse(
            payload["stream"]
        )

        self.assertEqual(
            payload["format"],
            schema,
        )

        self.assertEqual(
            payload["options"][
                "temperature"
            ],
            0.0,
        )

        self.assertEqual(
            payload["options"][
                "num_predict"
            ],
            200,
        )

        self.assertEqual(
            payload["messages"][0][
                "role"
            ],
            "system",
        )

        self.assertEqual(
            payload["messages"][1][
                "role"
            ],
            "user",
        )

    @patch(
        "workflow.services.ai.providers."
        "ollama.requests.post"
    )
    def test_text_response_is_normalized(
        self,
        post_mock,
    ):
        response = Mock()

        response.raise_for_status.return_value = (
            None
        )

        response.json.return_value = {
            "model":
                "local-test-model",

            "message": {
                "role": "assistant",
                "content": "ONEUCH_OK",
            },

            "done": True,
            "prompt_eval_count": 10,
            "eval_count": 2,
        }

        post_mock.return_value = response

        result = OllamaProvider(
            base_url=(
                "http://127.0.0.1:11434"
            )
        ).execute(
            AIRequest(
                prompt="Return ONEUCH_OK.",
                response_type="text",
                model="local-test-model",
            )
        )

        self.assertTrue(
            result.success
        )

        self.assertEqual(
            result.output,
            "ONEUCH_OK",
        )

        payload = (
            post_mock.call_args.kwargs[
                "json"
            ]
        )

        self.assertNotIn(
            "format",
            payload,
        )

    @patch(
        "workflow.services.ai.providers."
        "ollama.requests.post"
    )
    def test_provider_http_failure_is_explicit(
        self,
        post_mock,
    ):
        response = Mock()

        response.raise_for_status.side_effect = (
            RuntimeError(
                "Ollama unavailable"
            )
        )

        post_mock.return_value = response

        provider = OllamaProvider(
            base_url=(
                "http://127.0.0.1:11434"
            )
        )

        with self.assertRaises(
            RuntimeError
        ):
            provider.execute(
                AIRequest(
                    prompt="Test.",
                    response_type="text",
                    model="local-test-model",
                )
            )
