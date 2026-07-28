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

from workflow.services.ai.contracts import (
    AIResult,
)

from workflow.tests.utils import (
    create_workflow,
)

from workflow.services.ai.governance import (
    AIGovernanceDecision,
)


class AINodeEnterpriseIntegrationTests(
    TestCase
):

    def _build_executor(
        self,
        configuration=None,
        runtime_context=None,
    ):

        workflow = create_workflow()

        node = WorkflowNode.objects.create(
            workflow=workflow,
            name="Enterprise AI",
            node_type=WorkflowNode.AI,
            configuration=(
                configuration or {}
            ),
        )

        instance = (
            WorkflowInstance.objects.create(
                workflow=workflow,
                organization=(
                    workflow.organization
                ),
                started_by=(
                    workflow.created_by
                ),
                context=(
                    runtime_context or {}
                ),
            )
        )

        token = WorkflowToken.objects.create(
            instance=instance,
            node=node,
        )

        context = (
            WorkflowExecutionContext(
                instance
            )
        )

        executor_class = (
            ExecutorFactory.get_executor(
                WorkflowNode.AI
            )
        )

        executor = executor_class(
            context,
            token,
        )

        return (
            executor,
            context,
            instance,
            node,
        )

    def test_mock_ai_execution(
        self,
    ):

        (
            executor,
            context,
            instance,
            node,
        ) = self._build_executor(
            configuration={
                "prompt":
                    "Summarize this workflow.",

                "response_type":
                    "summary",
            }
        )

        result = executor.execute()

        self.assertTrue(result)

        output = context.get(
            "last_ai_result"
        )

        self.assertTrue(
            output["success"]
        )

        self.assertTrue(
            output["processed"]
        )

        self.assertEqual(
            output["provider"],
            "mock",
        )

        self.assertEqual(
            output["response_type"],
            "summary",
        )

        self.assertEqual(
            output["output"]["summary"],
            "Mock Summary",
        )

        self.assertEqual(
            len(
                context.get(
                    "ai_results"
                )
            ),
            1,
        )

    @patch(
        "workflow.services.executors.ai."
        "AIExecutionService.execute"
    )
    def test_failed_ai_execution_stops_node(
        self,
        execute_mock,
    ):

        execute_mock.return_value = (
            AIResult(
                success=False,
                output=None,
                provider="mock",
                model="mock-model",
                error="AI unavailable",
                confidence=0.0,
            )
        )

        (
            executor,
            context,
            _,
            _,
        ) = self._build_executor(
            configuration={
                "prompt": "Process this",
                "fail_on_error": True,
            }
        )

        result = executor.execute()

        self.assertFalse(result)

        self.assertTrue(
            context.get(
                "ai_failed"
            )
        )

        output = context.get(
            "last_ai_result"
        )

        self.assertFalse(
            output["success"]
        )

        self.assertEqual(
            output["error"],
            "AI unavailable",
        )

    @patch(
        "workflow.services.executors.ai."
        "AIExecutionService.execute"
    )
    def test_failed_ai_execution_can_continue(
        self,
        execute_mock,
    ):

        execute_mock.return_value = (
            AIResult(
                success=False,
                output=None,
                provider="mock",
                model="mock-model",
                error="Temporary failure",
                confidence=0.0,
            )
        )

        (
            executor,
            context,
            _,
            _,
        ) = self._build_executor(
            configuration={
                "prompt": "Process this",
                "fail_on_error": False,
            }
        )

        result = executor.execute()

        self.assertTrue(result)

        self.assertTrue(
            context.get(
                "ai_failed"
            )
        )

    @patch(
        "workflow.services.executors.ai."
        "AIExecutionService.execute"
    )
    def test_runtime_context_reaches_request(
        self,
        execute_mock,
    ):

        execute_mock.return_value = (
            AIResult(
                success=True,
                output="OK",
                provider="mock",
                model="mock-model",
            )
        )

        (
            executor,
            _,
            _,
            _,
        ) = self._build_executor(
            configuration={
                "prompt": "Analyze",
            },
            runtime_context={
                "priority": 90,
                "department": "finance",
            },
        )

        executor.execute()

        request = (
            execute_mock.call_args
            .kwargs["request"]
        )

        self.assertEqual(
            request.context[
                "runtime"
            ]["priority"],
            90,
        )

        self.assertEqual(
            request.context[
                "runtime"
            ]["department"],
            "finance",
        )

    @patch(
        "workflow.services.executors.ai."
        "AIExecutionService.execute"
    )
    def test_runtime_context_can_be_disabled(
        self,
        execute_mock,
    ):

        execute_mock.return_value = (
            AIResult(
                success=True,
                output="OK",
                provider="mock",
                model="mock-model",
            )
        )

        (
            executor,
            _,
            _,
            _,
        ) = self._build_executor(
            configuration={
                "prompt": "Analyze",

                "include_runtime_context":
                    False,
            },
            runtime_context={
                "secret_runtime_value":
                    "not-required",
            },
        )

        executor.execute()

        request = (
            execute_mock.call_args
            .kwargs["request"]
        )

        self.assertEqual(
            request.context[
                "runtime"
            ],
            {},
        )

    @patch(
        "workflow.services.executors.ai."
        "AIGovernanceEngine.evaluate"
    )
    @patch(
        "workflow.services.executors.ai."
        "AIExecutionService.execute"
    )
    def test_review_required_creates_pending_review(
        self,
        execute_mock,
        governance_mock,
    ):

        execute_mock.return_value = (
            AIResult(
                success=True,
                output={
                    "summary":
                        "Invoice appears valid",
                },
                provider="mock",
                model="mock-model",
                confidence=0.82,
            )
        )

        governance_mock.return_value = (
            AIGovernanceDecision(
                outcome="REVIEW",
                allowed=False,
                requires_review=True,
                blocked=False,
                confidence=0.82,
                reason=(
                    "Human approval required"
                ),
                policy_name="high_risk",
            )
        )

        (
            executor,
            context,
            _,
            _,
        ) = self._build_executor(
            configuration={
                "prompt":
                    "Analyze invoice",

                "response_type":
                    "summary",

                "governance_policy":
                    "high_risk",
            }
        )

        result = executor.execute()

        self.assertTrue(result)

        self.assertTrue(
            context.get(
                "ai_review_pending"
            )
        )

        review = context.get(
            "ai_pending_review"
        )

        self.assertIsNotNone(review)

        self.assertEqual(
            review["status"],
            "PENDING",
        )

        self.assertEqual(
            review["review_type"],
            "AI_GOVERNANCE",
        )

        self.assertEqual(
            review["governance_outcome"],
            "REVIEW",
        )

        self.assertEqual(
            review["policy_name"],
            "high_risk",
        )

        self.assertEqual(
            review["confidence"],
            0.82,
        )

        self.assertEqual(
            review["ai_output"],
            {
                "summary":
                    "Invoice appears valid",
            },
        )

        self.assertEqual(
            len(
                context.get(
                    "ai_pending_reviews"
                )
            ),
            1,
        )

        output = context.get(
            "last_ai_result"
        )

        self.assertIsNotNone(
            output["review"]
        )

        self.assertFalse(
            output[
                "governance"
            ]["can_execute"]
        )

    @patch(
        "workflow.services.executors.ai."
        "AIGovernanceEngine.evaluate"
    )
    @patch(
        "workflow.services.executors.ai."
        "AIExecutionService.execute"
    )
    def test_allowed_ai_does_not_create_review(
        self,
        execute_mock,
        governance_mock,
    ):

        execute_mock.return_value = (
            AIResult(
                success=True,
                output="OK",
                provider="mock",
                model="mock-model",
                confidence=0.98,
            )
        )

        governance_mock.return_value = (
            AIGovernanceDecision(
                outcome="ALLOW",
                allowed=True,
                requires_review=False,
                blocked=False,
                confidence=0.98,
                reason="Allowed",
                policy_name="default",
            )
        )

        (
            executor,
            context,
            _,
            _,
        ) = self._build_executor(
            configuration={
                "prompt": "Analyze",
            }
        )

        result = executor.execute()

        self.assertTrue(result)

        self.assertFalse(
            context.get(
                "ai_review_pending"
            )
        )

        self.assertIsNone(
            context.get(
                "ai_pending_review"
            )
        )

        output = context.get(
            "last_ai_result"
        )

        self.assertIsNone(
            output["review"]
        )

        self.assertTrue(
            output[
                "governance"
            ]["can_execute"]
        )

    @patch(
        "workflow.services.executors.ai."
        "AIGovernanceEngine.evaluate"
    )
    @patch(
        "workflow.services.executors.ai."
        "AIExecutionService.execute"
    )
    def test_blocked_ai_does_not_create_review(
        self,
        execute_mock,
        governance_mock,
    ):

        execute_mock.return_value = (
            AIResult(
                success=True,
                output="Unsafe result",
                provider="mock",
                model="mock-model",
                confidence=0.20,
            )
        )

        governance_mock.return_value = (
            AIGovernanceDecision(
                outcome="BLOCK",
                allowed=False,
                requires_review=False,
                blocked=True,
                confidence=0.20,
                reason="Below policy threshold",
                policy_name="default",
            )
        )

        (
            executor,
            context,
            _,
            _,
        ) = self._build_executor(
            configuration={
                "prompt": "Analyze",
            }
        )

        result = executor.execute()

        self.assertTrue(
            result
        )

        # ---------------------------------------------------------
        # AI execution completed successfully
        # ---------------------------------------------------------

        ai_result = context.get(
            "last_ai_result"
        )

        self.assertIsInstance(
            ai_result,
            dict,
        )

        self.assertTrue(
            ai_result.get(
                "success"
            )
        )

        # ---------------------------------------------------------
        # Governance must be BLOCKED
        # ---------------------------------------------------------

        governance = context.get(
            "ai_governance"
        )

        self.assertIsInstance(
            governance,
            dict,
        )

        self.assertEqual(
            governance.get(
                "outcome"
            ),
            "BLOCK",
        )

        self.assertTrue(
            governance.get(
                "blocked"
            )
        )

        self.assertFalse(
            governance.get(
                "allowed"
            )
        )

        self.assertFalse(
            governance.get(
                "requires_review"
            )
        )

        self.assertFalse(
            governance.get(
                "can_execute"
            )
        )

        self.assertEqual(
            governance.get(
                "reason"
            ),
            "Below policy threshold",
        )

        # ---------------------------------------------------------
        # BLOCK must NOT create human review
        # ---------------------------------------------------------

        review = context.get(
            "ai_pending_review"
        )

        self.assertIsNone(
            review
        )

        self.assertFalse(
            context.get(
                "ai_review_pending",
                False,
            )
        )

        # ---------------------------------------------------------
        # BLOCK must NOT suspend for human review
        # ---------------------------------------------------------

        self.assertFalse(
            context.is_suspended
        )

        self.assertFalse(
            context.get(
                "workflow_suspended",
                False,
            )
        )

        self.assertIsNone(
            context.get(
                "suspension_reason"
            )
        )

        self.assertEqual(
            context.get(
                "suspension_metadata",
                {},
            ),
            {}
        )