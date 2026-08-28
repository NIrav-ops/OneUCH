from unittest.mock import patch

from django.test import (
    SimpleTestCase,
    override_settings,
)

from workflow.services.ai.contracts import (
    AIRequest,
    AIResult,
)
from workflow.services.ai.service import (
    AIExecutionService,
)


class AIProcessingProvenanceTests(
    SimpleTestCase
):

    @override_settings(
        ONEUCH_AI_MODE="cloud"
    )
    @patch(
        "workflow.services.ai.providers.mock."
        "MockAIProvider.execute"
    )
    def test_cloud_success_has_processing_provenance(
        self,
        execute_mock,
    ):
        execute_mock.return_value = AIResult(
            success=True,
            output="OK",
            provider="mock",
            model="mock-model",
            metadata={
                "provider_metadata":
                    "preserved",
            },
        )

        result = AIExecutionService.execute(
            AIRequest(
                prompt="Test.",
                response_type="text",
            ),
            provider="mock",
        )

        self.assertTrue(
            result.success
        )

        self.assertEqual(
            result.metadata[
                "processing_mode"
            ],
            "cloud",
        )

        self.assertTrue(
            result.metadata[
                "governance_allowed"
            ]
        )

        self.assertEqual(
            result.metadata[
                "governance_provider"
            ],
            "mock",
        )

        self.assertEqual(
            result.metadata[
                "provider_metadata"
            ],
            "preserved",
        )

    @override_settings(
        ONEUCH_AI_MODE="local"
    )
    @patch(
        "workflow.services.ai.providers.ollama."
        "OllamaProvider.execute"
    )
    def test_local_success_has_processing_provenance(
        self,
        execute_mock,
    ):
        execute_mock.return_value = AIResult(
            success=True,
            output="LOCAL_OK",
            provider="ollama",
            model="local-model",
        )

        result = AIExecutionService.execute(
            AIRequest(
                prompt="Local test.",
                response_type="text",
                model="local-model",
            ),
            provider="ollama",
        )

        self.assertTrue(
            result.success
        )

        self.assertEqual(
            result.metadata[
                "processing_mode"
            ],
            "local",
        )

        self.assertEqual(
            result.metadata[
                "governance_provider"
            ],
            "ollama",
        )

    @override_settings(
        ONEUCH_AI_MODE="deterministic_only"
    )
    @patch(
        "workflow.services.ai.service."
        "AIProviderRouter.get_provider"
    )
    def test_blocked_result_records_deterministic_mode(
        self,
        router_mock,
    ):
        result = AIExecutionService.execute(
            AIRequest(
                prompt="Sensitive.",
                response_type="text",
            ),
            provider="openai",
        )

        self.assertFalse(
            result.success
        )

        self.assertEqual(
            result.metadata[
                "processing_mode"
            ],
            "deterministic_only",
        )

        self.assertFalse(
            result.metadata[
                "governance_allowed"
            ]
        )

        self.assertEqual(
            result.metadata[
                "failure_stage"
            ],
            "execution_governance",
        )

        router_mock.assert_not_called()
