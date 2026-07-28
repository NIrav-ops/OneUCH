from django.test import TestCase

from workflow.models import (
    WorkflowNode,
    WorkflowInstance,
    WorkflowToken,
)

from workflow.services.context import (
    WorkflowExecutionContext,
)

from workflow.services.executors.ai import (
    AINodeExecutor,
)

from workflow.tests.utils import (
    create_workflow,
)

from unittest.mock import patch

from workflow.services.ai.models import (
    AIResult,
)


class AINodeExecutorTests(TestCase):

    def setUp(self):

        self.workflow = create_workflow()

        self.node = WorkflowNode.objects.create(
            workflow=self.workflow,
            name="Analyze Purchase Request",
            node_type=WorkflowNode.AI,
            configuration={
                "prompt": (
                    "Analyze this purchase request "
                    "and return a recommendation."
                ),
                "provider": "mock",
                "model": "default",
                "temperature": 0.2,
                "max_tokens": 500,
            },
        )

        self.instance = WorkflowInstance.objects.create(
            workflow=self.workflow,
            organization=self.workflow.organization,
            started_by=self.workflow.created_by,
            context={
                "purchase_amount": 50000,
                "department": "Finance",
            },
        )

        self.token = WorkflowToken.objects.create(
            instance=self.instance,
            node=self.node,
        )

        self.context = WorkflowExecutionContext(
            self.instance
        )

    @patch(
        "workflow.services.executors.ai."
        "AIExecutionService.execute"
    )
    def test_ai_failure_returns_false(
        self,
        mock_execute,
    ):

        mock_execute.return_value = AIResult(
            success=False,
            output=None,
            provider="mock",
            model="default",
            confidence=0.0,
            error="Provider failed",
        )

        self.node.configuration[
            "fail_on_error"
        ] = True

        self.node.save(
            update_fields=[
                "configuration",
            ]
        )

        executor = AINodeExecutor(
            self.context,
            self.token,
        )

        success = executor.execute()

        self.assertFalse(
            success
        )

        self.assertTrue(
            self.context.get(
                "ai_failed"
            )
        )

        result = self.context.get(
            "last_ai_result"
        )

        self.assertFalse(
            result["success"]
        )

        self.assertEqual(
            result["error"],
            "Provider failed",
        )

    @patch(
        "workflow.services.executors.ai."
        "AIExecutionService.execute"
    )
    def test_noncritical_ai_failure_continues(
        self,
        mock_execute,
    ):

        mock_execute.return_value = AIResult(
            success=False,
            output=None,
            provider="mock",
            model="default",
            confidence=0.0,
            error="Provider failed",
        )

        self.node.configuration[
            "fail_on_error"
        ] = False

        self.node.save(
            update_fields=[
                "configuration",
            ]
        )

        executor = AINodeExecutor(
            self.context,
            self.token,
        )

        success = executor.execute()

        self.assertTrue(
            success
        )

        self.assertTrue(
            self.context.get(
                "ai_failed"
            )
        )

        result = self.context.get(
            "last_ai_result"
        )

        self.assertFalse(
            result["success"]
        )

    def test_last_ai_result_is_recorded(self):

        executor = AINodeExecutor(
            self.context,
            self.token,
        )

        executor.execute()

        last_result = self.context.get(
            "last_ai_result"
        )

        self.assertIsNotNone(
            last_result
        )

        self.assertEqual(
            last_result["node"],
            self.node.name,
        )

        self.assertTrue(
            last_result["success"]
        )

    def test_ai_executor_executes_successfully(self):

        executor = AINodeExecutor(
            self.context,
            self.token,
        )

        success = executor.execute()

        self.assertTrue(success)

        results = self.context.get(
            "ai_results"
        )

        self.assertIsNotNone(results)

        self.assertEqual(
            len(results),
            1,
        )

        result = results[0]

        self.assertTrue(
            result["processed"]
        )

        self.assertTrue(
            result["success"]
        )

        self.assertEqual(
            result["node"],
            "Analyze Purchase Request",
        )

        self.assertEqual(
            result["node_id"],
            str(self.node.id),
        )

    def test_ai_executor_records_provider(self):

        executor = AINodeExecutor(
            self.context,
            self.token,
        )

        executor.execute()

        result = self.context.get(
            "ai_results"
        )[0]

        self.assertEqual(
            result["provider"],
            "mock",
        )

    def test_ai_executor_records_output(self):

        executor = AINodeExecutor(
            self.context,
            self.token,
        )

        executor.execute()

        result = self.context.get(
            "ai_results"
        )[0]

        self.assertIn(
            "output",
            result,
        )

        self.assertIsNotNone(
            result["output"]
        )

    def test_ai_executor_preserves_existing_results(self):

        self.context.set(
            "ai_results",
            [
                {
                    "node": "Previous AI Node",
                    "processed": True,
                }
            ],
        )

        executor = AINodeExecutor(
            self.context,
            self.token,
        )

        executor.execute()

        results = self.context.get(
            "ai_results"
        )

        self.assertEqual(
            len(results),
            2,
        )

        self.assertEqual(
            results[0]["node"],
            "Previous AI Node",
        )

        self.assertEqual(
            results[1]["node"],
            "Analyze Purchase Request",
        )

    def test_ai_executor_uses_node_configuration(self):

        self.node.configuration = {
            "prompt": "Classify enterprise request",
            "provider": "mock",
            "model": "enterprise-test-model",
            "temperature": 0.1,
            "max_tokens": 250,
        }

        self.node.save(
            update_fields=[
                "configuration",
            ]
        )

        executor = AINodeExecutor(
            self.context,
            self.token,
        )

        executor.execute()

        result = self.context.get(
            "ai_results"
        )[0]

        self.assertEqual(
            result["model"],
            "enterprise-test-model",
        )