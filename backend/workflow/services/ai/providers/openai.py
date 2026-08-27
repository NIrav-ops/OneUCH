import json
import logging
import os
import time

from workflow.services.ai.contracts import (
    AIRequest,
    AIResult,
)
from workflow.services.ai.providers.base import (
    BaseAIProvider,
)


logger = logging.getLogger(__name__)


class OpenAIProvider(BaseAIProvider):
    """
    Production OpenAI provider for One UCH.

    Translates provider-neutral AIRequest into the
    OpenAI Responses API and normalizes the result
    back into AIResult.

    This provider never performs domain writes.
    """

    provider_name = "openai"

    default_model = (
        "gpt-5.6-luna"
    )

    def __init__(
        self,
        *,
        api_key=None,
        timeout=None,
    ):
        self.api_key = (
            api_key
            or os.getenv(
                "OPENAI_API_KEY"
            )
        )

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

    def _build_client(self):
        if not self.api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not configured."
            )

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "OpenAI Python package is not installed."
            ) from exc

        return OpenAI(
            api_key=self.api_key,
            timeout=self.timeout,
        )

    @staticmethod
    def _build_input(
        request: AIRequest,
    ):
        messages = []

        if request.system_prompt:
            messages.append(
                {
                    "role": "system",
                    "content": (
                        request.system_prompt
                    ),
                }
            )

        messages.append(
            {
                "role": "user",
                "content": request.prompt,
            }
        )

        return messages

    @staticmethod
    def _parse_output(
        request: AIRequest,
        output_text: str,
    ):
        if request.response_type in {
            "json",
            "classification",
            "summary",
            "decision",
            "action_list",
            "approval_recommendation",
        }:
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

        client = (
            self._build_client()
        )

        model = (
            request.model
            or os.getenv(
                "ONEUCH_AI_MODEL"
            )
            or self.default_model
        )

        started_at = (
            time.perf_counter()
        )

        request_kwargs = {
            "model": model,
            "input": self._build_input(
                request
            ),
            "max_output_tokens": (
                request.max_tokens
            ),
        }

        # --------------------------------------------------
        # Structured Outputs
        #
        # When the caller supplies a response_schema for a
        # structured response type, require the provider to
        # generate schema-conforming JSON.
        # --------------------------------------------------

        if (
            request.response_schema
            and request.response_type
            in {
                "json",
                "classification",
                "summary",
                "decision",
                "action_list",
                "approval_recommendation",
            }
        ):
            request_kwargs["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": (
                        f"oneuch_{request.response_type}"
                    ),
                    "strict": True,
                    "schema": request.response_schema,
                }
            }

        # GPT-5.6 reasoning models reject the
        # temperature parameter. Preserve AIRequest's
        # provider-neutral temperature field for models
        # that support it, but do not send an unsupported
        # provider parameter.
        if not model.startswith(
            "gpt-5.6"
        ):
            request_kwargs[
                "temperature"
            ] = request.temperature

        response = (
            client.responses.create(
                **request_kwargs
            )
        )

        execution_time_ms = int(
            (
                time.perf_counter()
                - started_at
            )
            * 1000
        )

        output_text = (
            response.output_text
            or ""
        )

        output = self._parse_output(
            request,
            output_text,
        )

        usage = getattr(
            response,
            "usage",
            None,
        )

        prompt_tokens = (
            getattr(
                usage,
                "input_tokens",
                0,
            )
            if usage
            else 0
        )

        completion_tokens = (
            getattr(
                usage,
                "output_tokens",
                0,
            )
            if usage
            else 0
        )

        total_tokens = (
            getattr(
                usage,
                "total_tokens",
                0,
            )
            if usage
            else (
                prompt_tokens
                + completion_tokens
            )
        )

        return AIResult(
            success=True,
            output=output,
            provider=(
                self.provider_name
            ),
            model=model,
            prompt_tokens=(
                prompt_tokens
            ),
            completion_tokens=(
                completion_tokens
            ),
            total_tokens=(
                total_tokens
            ),
            execution_time_ms=(
                execution_time_ms
            ),
            confidence=1.0,
            metadata={
                "response_id":
                    getattr(
                        response,
                        "id",
                        None,
                    ),
                "api":
                    "responses",
            },
        )
