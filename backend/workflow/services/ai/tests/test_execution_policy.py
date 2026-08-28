from unittest.mock import patch

from django.test import (
    SimpleTestCase,
    override_settings,
)

from workflow.services.ai.contracts import (
    AIRequest,
)
from workflow.services.ai.service import (
    AIExecutionService,
)
from workflow.services.ai.exceptions import (
    ProviderNotFound,
)
from workflow.services.ai.governance.execution_policy import (
    AIExecutionPolicy,
)


class AIExecutionPolicyTests(
    SimpleTestCase
):

    def test_deterministic_only_blocks_cloud_ai(
        self,
    ):
        decision = AIExecutionPolicy.evaluate(
            mode="deterministic_only",
            provider="openai",
        )

        self.assertFalse(
            decision.allowed
        )

    def test_cloud_allows_openai(
        self,
    ):
        decision = AIExecutionPolicy.evaluate(
            mode="cloud",
            provider="openai",
        )

        self.assertTrue(
            decision.allowed
        )

    def test_cloud_blocks_ollama(
        self,
    ):
        decision = AIExecutionPolicy.evaluate(
            mode="cloud",
            provider="ollama",
        )

        self.assertFalse(
            decision.allowed
        )

    def test_local_allows_ollama(
        self,
    ):
        decision = AIExecutionPolicy.evaluate(
            mode="local",
            provider="ollama",
        )

        self.assertTrue(
            decision.allowed
        )

    def test_local_blocks_openai(
        self,
    ):
        decision = AIExecutionPolicy.evaluate(
            mode="local",
            provider="openai",
        )

        self.assertFalse(
            decision.allowed
        )

    def test_unknown_mode_is_fail_closed(
        self,
    ):
        decision = AIExecutionPolicy.evaluate(
            mode="unknown",
            provider="openai",
        )

        self.assertFalse(
            decision.allowed
        )

    @override_settings(
        ONEUCH_AI_MODE="cloud"
    )
    def test_cloud_unknown_provider_preserves_hardening_contract(
        self,
    ):
        with self.assertRaises(
            ProviderNotFound
        ):
            AIExecutionService.execute(
                AIRequest(
                    prompt="Test communication.",
                    response_type="text",
                ),
                provider="unknown",
            )

    @override_settings(
        ONEUCH_AI_MODE="deterministic_only"
    )
    @patch(
        "workflow.services.ai.service."
        "AIProviderRouter.get_provider"
    )
    def test_service_blocks_before_provider_resolution(
        self,
        router_mock,
    ):
        result = AIExecutionService.execute(
            AIRequest(
                prompt="Sensitive communication.",
                response_type="text",
            ),
            provider="openai",
        )

        self.assertFalse(
            result.success
        )

        self.assertEqual(
            result.metadata[
                "failure_stage"
            ],
            "execution_governance",
        )

        self.assertFalse(
            result.metadata[
                "retryable"
            ]
        )

        router_mock.assert_not_called()

    @override_settings(
        ONEUCH_AI_MODE="local"
    )
    @patch(
        "workflow.services.ai.providers."
        "ollama.OllamaProvider.execute"
    )
    def test_local_mode_executes_ollama(
        self,
        execute_mock,
    ):
        from workflow.services.ai.contracts import (
            AIResult,
        )

        execute_mock.return_value = AIResult(
            success=True,
            output="ONEUCH_LOCAL_OK",
            provider="ollama",
            model="local-test-model",
            confidence=1.0,
        )

        result = AIExecutionService.execute(
            AIRequest(
                prompt="Local test.",
                response_type="text",
                model="local-test-model",
            ),
            provider="ollama",
        )

        self.assertTrue(
            result.success
        )

        self.assertEqual(
            result.provider,
            "ollama",
        )

        execute_mock.assert_called_once()

    @override_settings(
        ONEUCH_AI_MODE="cloud"
    )
    @patch(
        "workflow.services.ai.providers."
        "ollama.OllamaProvider.execute"
    )
    def test_cloud_mode_blocks_ollama_before_execution(
        self,
        execute_mock,
    ):
        result = AIExecutionService.execute(
            AIRequest(
                prompt="Cloud policy test.",
                response_type="text",
                model="local-test-model",
            ),
            provider="ollama",
        )

        self.assertFalse(
            result.success
        )

        self.assertEqual(
            result.metadata[
                "failure_stage"
            ],
            "execution_governance",
        )

        execute_mock.assert_not_called()

