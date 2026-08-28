import json
import os
import time

import requests

from workflow.services.ai.contracts import (
    AIRequest,
    AIResult,
)
from workflow.services.ai.providers.base import (
    BaseAIProvider,
)


class OllamaProvider(BaseAIProvider):
    """
    Local/private Ollama provider for One UCH.

    Communication is sent only to the configured Ollama
    endpoint. This provider performs no domain/database writes.
    """

    provider_name = "ollama"

    default_base_url = (
        "http://127.0.0.1:11434"
    )

    STRUCTURED_RESPONSE_TYPES = {
        "json",
        "classification",
        "summary",
        "decision",
        "action_list",
        "approval_recommendation",
    }

    def __init__(
        self,
        *,
        base_url=None,
        timeout=None,
    ):
        self.base_url = (
            base_url
            or os.getenv(
                "ONEUCH_OLLAMA_BASE_URL",
                self.default_base_url,
            )
        ).rstrip("/")

        self.timeout = (
            timeout
            if timeout is not None
            else float(
                os.getenv(
                    "ONEUCH_AI_TIMEOUT_SECONDS",
                    "30",
                )
            )
        )

    @staticmethod
    def _build_messages(
        request: AIRequest,
    ):
        messages = []

        if request.system_prompt:
            messages.append(
                {
                    "role": "system",
                    "content":
                        request.system_prompt,
                }
            )

        messages.append(
            {
                "role": "user",
                "content": request.prompt,
            }
        )

        return messages

    @classmethod
    def _parse_output(
        cls,
        request: AIRequest,
        output_text,
    ):
        output_text = (
            output_text
            if isinstance(
                output_text,
                str,
            )
            else str(
                output_text or ""
            )
        )

        if (
            request.response_type
            in cls.STRUCTURED_RESPONSE_TYPES
        ):
            return json.loads(
                output_text
            )

        if (
            request.response_type
            == "boolean"
        ):
            normalized = (
                output_text
                .strip()
                .lower()
            )

            if normalized == "true":
                return True

            if normalized == "false":
                return False

            raise ValueError(
                "AI boolean output must be "
                "'true' or 'false'."
            )

        if (
            request.response_type
            == "number"
        ):
            return float(
                output_text.strip()
            )

        return output_text

    def execute(
        self,
        request: AIRequest,
    ) -> AIResult:

        self.validate_request(
            request
        )

        model = (
            request.model
            or os.getenv(
                "ONEUCH_AI_MODEL"
            )
        )

        if not model:
            raise RuntimeError(
                "ONEUCH_AI_MODEL is not configured "
                "for Ollama."
            )

        payload = {
            "model": model,
            "messages":
                self._build_messages(
                    request
                ),
            "stream": False,
        }

        # --------------------------------------------------
        # Structured output
        #
        # Ollama accepts either "json" or a JSON schema
        # directly in the format property.
        # --------------------------------------------------

        if (
            request.response_type
            in self.STRUCTURED_RESPONSE_TYPES
        ):
            payload["format"] = (
                request.response_schema
                if request.response_schema
                else "json"
            )

        options = {}

        if (
            request.temperature
            is not None
        ):
            options["temperature"] = (
                request.temperature
            )

        if (
            request.max_tokens
            is not None
        ):
            options["num_predict"] = (
                request.max_tokens
            )

        if options:
            payload["options"] = options

        started_at = (
            time.perf_counter()
        )

        response = requests.post(
            (
                f"{self.base_url}"
                "/api/chat"
            ),
            json=payload,
            timeout=self.timeout,
        )

        response.raise_for_status()

        data = response.json()

        execution_time_ms = int(
            (
                time.perf_counter()
                - started_at
            )
            * 1000
        )

        message = (
            data.get("message")
            or {}
        )

        output_text = (
            message.get("content")
            or ""
        )

        output = self._parse_output(
            request,
            output_text,
        )

        prompt_tokens = int(
            data.get(
                "prompt_eval_count"
            )
            or 0
        )

        completion_tokens = int(
            data.get(
                "eval_count"
            )
            or 0
        )

        return AIResult(
            success=True,
            output=output,
            provider=(
                self.provider_name
            ),
            model=(
                data.get("model")
                or model
            ),
            prompt_tokens=(
                prompt_tokens
            ),
            completion_tokens=(
                completion_tokens
            ),
            total_tokens=(
                prompt_tokens
                + completion_tokens
            ),
            execution_time_ms=(
                execution_time_ms
            ),

            # Ollama's standard chat response does not
            # provide a normalized business-confidence
            # value. Domain candidates continue to supply
            # their own confidence as they already do.
            confidence=1.0,

            metadata={
                "api":
                    "ollama_chat",

                "local":
                    True,

                "done":
                    bool(
                        data.get("done")
                    ),

                "done_reason":
                    data.get(
                        "done_reason"
                    ),
            },
        )
