from unittest.mock import patch

from django.test import TestCase

from inbox.models import Organization

from workflow.models import (
    WorkflowDefinition,
    WorkflowInstance,
    WorkflowNode,
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
        "workflow.services.runtime_engine.WorkflowExecutionEventService.record"
    )
    def test_runtime_failure_records_failure_events(
        self,
        record_event,
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
        ):

            engine.run()

        failure_calls = []

        for call in record_event.call_args_list:

            event = call.kwargs.get(
                "event"
            )

            if event in [
                WorkflowExecutionEventService.NODE_FAILED,
                WorkflowExecutionEventService.WORKFLOW_FAILED,
            ]:

                failure_calls.append(
                    call
                )

        self.assertEqual(
            len(failure_calls),
            2,
        )

        node_failure = (
            failure_calls[0]
        )

        workflow_failure = (
            failure_calls[1]
        )

        node_failure_details = (
            node_failure.kwargs.get(
                "details"
            )
        )

        workflow_failure_details = (
            workflow_failure.kwargs.get(
                "details"
            )
        )

        self.assertEqual(
            node_failure_details[
                "error_type"
            ],
            "RuntimeError",
        )

        self.assertEqual(
            node_failure_details[
                "error_message"
            ],
            "Intentional runtime failure.",
        )

        self.assertEqual(
            workflow_failure_details[
                "error_type"
            ],
            "RuntimeError",
        )

        self.assertEqual(
            workflow_failure_details[
                "error_message"
            ],
            "Intentional runtime failure.",
        )