from unittest.mock import patch

from django.test import TestCase

from workflow.models import (
    WorkflowNode,
    WorkflowInstance,
    WorkflowToken,
)

from workflow.services.context import (
    WorkflowExecutionContext,
)

from workflow.services.executors.factory import (
    ExecutorFactory,
)

from workflow.services.ai import (
    AIResult,
)

from workflow.tests.utils import (
    create_workflow,
)


class AIGovernanceRuntimeIntegrationTests(
    TestCase
):

    def _build_execution(
        self,
        configuration=None,
    ):

        workflow = create_workflow()

        node = WorkflowNode.objects.create(
            workflow=workflow,
            name="Enterprise AI",
            node_type=WorkflowNode.AI,
            configuration=configuration or {},
        )

        instance = WorkflowInstance.objects.create(
            workflow=workflow,
            organization=workflow.organization,
            started_by=workflow.created_by,
        )

        token = WorkflowToken.objects.create(
            instance=instance,
            node=node,
        )

        context = WorkflowExecutionContext(
            instance
        )

        executor = (
            ExecutorFactory.get_executor(
                WorkflowNode.AI
            )(
                context,
                token,
            )
        )

        return (
            executor,
            context,
            instance,
            node,
        )

    def test_default_policy_requires_review(
        self,
    ):

        (
            executor,
            context,
            _,
            _,
        ) = self._build_execution(
            {
                "prompt":
                    "Summarize the communication.",

                "response_type":
                    "summary",

                "governance_policy":
                    "default",
            }
        )

        result = executor.execute()

        self.assertTrue(
            result
        )

        governance = context.get(
            "ai_governance"
        )

        self.assertEqual(
            governance["outcome"],
            "review",
        )

        self.assertTrue(
            governance[
                "requires_review"
            ]
        )

        self.assertFalse(
            governance[
                "can_execute"
            ]
        )

        self.assertTrue(
            context.get(
                "ai_requires_review"
            )
        )

        self.assertFalse(
            context.get(
                "ai_blocked"
            )
        )

    def test_controlled_automation_can_allow(
        self,
    ):

        (
            executor,
            context,
            _,
            _,
        ) = self._build_execution(
            {
                "prompt":
                    "Summarize the communication.",

                "response_type":
                    "summary",

                "governance_policy":
                    "controlled_automation",
            }
        )

        result = executor.execute()

        self.assertTrue(
            result
        )

        governance = context.get(
            "ai_governance"
        )

        self.assertEqual(
            governance["outcome"],
            "allow",
        )

        self.assertTrue(
            governance["allowed"]
        )

        self.assertTrue(
            governance[
                "can_execute"
            ]
        )

        self.assertFalse(
            context.get(
                "ai_requires_review"
            )
        )

        self.assertFalse(
            context.get(
                "ai_blocked"
            )
        )

    def test_approval_recommendation_requires_review(
        self,
    ):

        (
            executor,
            context,
            _,
            _,
        ) = self._build_execution(
            {
                "prompt":
                    "Recommend whether approval "
                    "should proceed.",

                "response_type":
                    "approval_recommendation",

                "governance_policy":
                    "controlled_automation",
            }
        )

        result = executor.execute()

        self.assertTrue(
            result
        )

        governance = context.get(
            "ai_governance"
        )

        self.assertEqual(
            governance["outcome"],
            "review",
        )

        self.assertTrue(
            governance[
                "requires_review"
            ]
        )

        self.assertFalse(
            governance[
                "can_execute"
            ]
        )

    @patch(
        "workflow.services.ai.providers.mock."
        "MockAIProvider.execute"
    )
    def test_low_confidence_result_is_blocked(
        self,
        mock_execute,
    ):

        mock_execute.return_value = AIResult(
            success=True,
            output={
                "summary":
                    "Low confidence summary",
            },
            provider="mock",
            model="mock-model",
            confidence=0.30,
        )

        (
            executor,
            context,
            _,
            _,
        ) = self._build_execution(
            {
                "prompt":
                    "Summarize the communication.",

                "response_type":
                    "summary",

                "governance_policy":
                    "default",
            }
        )

        result = executor.execute()

        self.assertTrue(
            result
        )

        governance = context.get(
            "ai_governance"
        )

        self.assertEqual(
            governance["outcome"],
            "block",
        )

        self.assertTrue(
            governance["blocked"]
        )

        self.assertFalse(
            governance[
                "can_execute"
            ]
        )

        self.assertTrue(
            context.get(
                "ai_blocked"
            )
        )

    @patch(
        "workflow.services.ai.providers.mock."
        "MockAIProvider.execute"
    )
    def test_provider_failure_marks_ai_failed(
        self,
        mock_execute,
    ):

        mock_execute.side_effect = (
            RuntimeError(
                "Provider unavailable"
            )
        )

        (
            executor,
            context,
            _,
            _,
        ) = self._build_execution(
            {
                "prompt":
                    "Process communication.",

                "response_type":
                    "text",

                "fail_on_error":
                    True,
            }
        )

        result = executor.execute()

        self.assertFalse(
            result
        )

        self.assertTrue(
            context.get(
                "ai_failed"
            )
        )

        self.assertTrue(
            context.get(
                "ai_blocked"
            )
        )

        governance = context.get(
            "ai_governance"
        )

        self.assertEqual(
            governance["outcome"],
            "block",
        )

    def test_governance_is_embedded_in_ai_result(
        self,
    ):

        (
            executor,
            context,
            _,
            _,
        ) = self._build_execution(
            {
                "prompt":
                    "Summarize communication.",

                "response_type":
                    "summary",

                "governance_policy":
                    "default",
            }
        )

        executor.execute()

        last_result = context.get(
            "last_ai_result"
        )

        self.assertIn(
            "governance",
            last_result,
        )

        self.assertEqual(
            last_result[
                "governance"
            ]["policy_name"],
            "default",
        )

    def test_ai_result_keeps_execution_metadata(
        self,
    ):

        (
            executor,
            context,
            _,
            node,
        ) = self._build_execution(
            {
                "prompt":
                    "Summarize communication.",

                "response_type":
                    "summary",
            }
        )

        executor.execute()

        result = context.get(
            "last_ai_result"
        )

        self.assertEqual(
            result["node"],
            node.name,
        )

        self.assertEqual(
            result["node_id"],
            str(node.id),
        )

        self.assertEqual(
            result["provider"],
            "mock",
        )

        self.assertIn(
            "total_tokens",
            result,
        )

        self.assertIn(
            "cost",
            result,
        )