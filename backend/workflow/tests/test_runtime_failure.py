from unittest.mock import patch

from django.test import TestCase

from inbox.models import Organization

from workflow.models import (
    WorkflowDefinition,
    WorkflowInstance,
    WorkflowNode,
    WorkflowTransition,
)

from workflow.services.runtime_engine import (
    WorkflowRuntimeEngine,
)

from workflow.services.runtime_controller import (
    RuntimeController,
)

from workflow.services.runtime_state import (
    RuntimeState,
)

from workflow.services.execution import (
    WorkflowExecutionEventService,
)


class WorkflowRuntimeFailureTests(
    TestCase
):

    def setUp(self):

        self.organization = (
            Organization.objects.create(
                name="Runtime Failure Organization",
                slug="runtime-failure-organization",
            )
        )

        self.workflow = (
            WorkflowDefinition.objects.create(
                organization=self.organization,
                name="Failure Workflow",
                code="FAILURE_WORKFLOW",
                version=1,
                status=(
                    WorkflowDefinition.STATUS_ACTIVE
                ),
            )
        )

        self.start_node = (
            WorkflowNode.objects.create(
                workflow=self.workflow,
                name="Start",
                node_type=WorkflowNode.START,
                configuration={},
            )
        )

        self.action_node = (
            WorkflowNode.objects.create(
                workflow=self.workflow,
                name="Failing Action",
                node_type=WorkflowNode.ACTION,
                configuration={},
            )
        )

        self.end_node = (
            WorkflowNode.objects.create(
                workflow=self.workflow,
                name="End",
                node_type=WorkflowNode.END,
                configuration={},
            )
        )

        #
        # Valid executable workflow graph:
        #
        # START -> ACTION -> END
        #
        # The ACTION node is deliberately used as the
        # failure injection point for this test.
        #

        WorkflowTransition.objects.create(
            workflow=self.workflow,
            source=self.start_node,
            target=self.action_node,
        )

        WorkflowTransition.objects.create(
            workflow=self.workflow,
            source=self.action_node,
            target=self.end_node,
        )

        self.instance = (
            WorkflowInstance.objects.create(
                workflow=self.workflow,
                organization=self.organization,
                context={},
            )
        )

    @patch(
        "workflow.services.runtime_engine.ExecutorFactory.get_executor"
    )
    def test_runtime_failure(
        self,
        get_executor,
    ):

        class FailingExecutor:

            def __init__(
                self,
                context,
                token,
            ):

                self.context = context
                self.token = token

            def execute(self):

                raise RuntimeError(
                    "Intentional runtime failure."
                )

        get_executor.return_value = (
            FailingExecutor
        )

        engine = WorkflowRuntimeEngine(
            self.instance
        )

        with self.assertRaises(
            RuntimeError
        ) as context:

            engine.run()

        self.assertEqual(
            str(context.exception),
            "Intentional runtime failure.",
        )

        self.instance.refresh_from_db()

        self.assertEqual(
            self.instance.status,
            WorkflowInstance.STATUS_FAILED,
        )

        self.assertIsNotNone(
            self.instance.completed_at
        )

        self.assertEqual(
            engine.controller.state,
            RuntimeState.FAILED,
        )

        self.assertFalse(
            engine.controller.is_completed
        )

    @patch(
        "workflow.services.runtime_engine.ExecutorFactory.get_executor"
    )
    @patch(
        "workflow.services.runtime_engine."
        "WorkflowExecutionEventService.record_failure"
    )
    def test_runtime_failure_records_failure_events(
        self,
        record_failure,
        get_executor,
    ):

        class FailingExecutor:

            def __init__(
                self,
                context,
                token,
            ):

                self.context = context
                self.token = token

            def execute(self):

                raise RuntimeError(
                    "Intentional runtime failure."
                )

        #
        # The test must inject the same deterministic
        # failing executor used by test_runtime_failure().
        #
        # Without this, the mocked executor factory does
        # not produce a failure and the workflow completes
        # normally.
        #

        get_executor.return_value = (
            FailingExecutor
        )

        engine = WorkflowRuntimeEngine(
            self.instance
        )

        with self.assertRaises(
            RuntimeError
        ) as context:

            engine.run()

        #
        # Confirm that the actual execution failure
        # reached the runtime boundary.
        #

        self.assertEqual(
            str(context.exception),
            "Intentional runtime failure.",
        )

        #
        # Failure evidence must contain exactly two
        # canonical failure events:
        #
        # 1. NODE_FAILED
        # 2. WORKFLOW_FAILED
        #

        self.assertEqual(
            record_failure.call_count,
            2,
        )

        calls = (
            record_failure.call_args_list
        )

        node_failure_call = None
        workflow_failure_call = None

        for call in calls:

            kwargs = call.kwargs

            if (
                kwargs.get("event")
                == (
                    WorkflowExecutionEventService
                    .NODE_FAILED
                )
            ):

                node_failure_call = kwargs

            elif (
                kwargs.get("event")
                == (
                    WorkflowExecutionEventService
                    .WORKFLOW_FAILED
                )
            ):

                workflow_failure_call = kwargs

        self.assertIsNotNone(
            node_failure_call
        )

        self.assertIsNotNone(
            workflow_failure_call
        )

        #
        # Both failure events must carry the original
        # exception into record_failure().
        #
        # record_failure() remains responsible for
        # safe classification and persistence.
        #

        self.assertIsInstance(
            node_failure_call["exception"],
            RuntimeError,
        )

        self.assertIsInstance(
            workflow_failure_call["exception"],
            RuntimeError,
        )

        #
        # Node failure must identify the actual
        # failing workflow node.
        #

        self.assertIsNotNone(
            node_failure_call["node"]
        )

        self.assertEqual(
            node_failure_call["node"].pk,
            self.start_node.pk,
        )

        #
        # Workflow failure is workflow-level and
        # therefore must not be attached to a node.
        #

        self.assertIsNone(
            workflow_failure_call.get(
                "node"
            )
        )