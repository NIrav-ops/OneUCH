from django.test import TestCase

from workflow.models import (
    WorkflowExecutionLog,
)

from workflow.services.execution import (
    WorkflowExecutionEventService,
)

from workflow.tests.utils import (
    create_workflow,
)

from workflow.models import (
    WorkflowInstance,
)


class WorkflowExecutionFailureEvidenceTests(
    TestCase
):

    def setUp(self):

        self.workflow = create_workflow()

        self.instance = (
            WorkflowInstance.objects.create(
                workflow=self.workflow,
                organization=self.workflow.organization,
            )
        )

    def test_node_failure_contains_safe_failure_classification(
        self,
    ):

        error = RuntimeError(
            "Sensitive provider response "
            "must never be persisted."
        )

        event = (
            WorkflowExecutionEventService
            .record_failure(
                instance=self.instance,
                node=None,
                event=(
                    WorkflowExecutionEventService
                    .NODE_FAILED
                ),
                exception=error,
            )
        )

        self.assertEqual(
            event.event,
            WorkflowExecutionEventService.NODE_FAILED,
        )

        self.assertEqual(
            event.details["failure_type"],
            (
                WorkflowExecutionEventService
                .FAILURE_TYPE_NODE_EXECUTION
            ),
        )

        self.assertEqual(
            event.details["failure_stage"],
            (
                WorkflowExecutionEventService
                .FAILURE_STAGE_NODE_EXECUTION
            ),
        )

        self.assertEqual(
            event.details["exception_type"],
            "RuntimeError",
        )

    def test_raw_exception_message_is_not_persisted(
        self,
    ):

        sensitive_message = (
            "Authorization token "
            "SECRET-TOKEN-123"
        )

        error = RuntimeError(
            sensitive_message
        )

        event = (
            WorkflowExecutionEventService
            .record_failure(
                instance=self.instance,
                event=(
                    WorkflowExecutionEventService
                    .NODE_FAILED
                ),
                exception=error,
            )
        )

        self.assertNotIn(
            sensitive_message,
            str(event.details),
        )

        self.assertNotIn(
            "SECRET-TOKEN-123",
            str(event.details),
        )

        self.assertNotIn(
            "error_message",
            event.details,
        )

    def test_caller_cannot_override_failure_classification(
        self,
    ):

        error = RuntimeError(
            "provider failure"
        )

        event = (
            WorkflowExecutionEventService
            .record_failure(
                instance=self.instance,
                event=(
                    WorkflowExecutionEventService
                    .NODE_FAILED
                ),
                exception=error,
                details={
                    "failure_type": "fake_failure",
                    "failure_stage": "fake_stage",
                    "exception_type": "FakeException",
                },
            )
        )

        self.assertEqual(
            event.details["failure_type"],
            (
                WorkflowExecutionEventService
                .FAILURE_TYPE_NODE_EXECUTION
            ),
        )

        self.assertEqual(
            event.details["failure_stage"],
            (
                WorkflowExecutionEventService
                .FAILURE_STAGE_NODE_EXECUTION
            ),
        )

        self.assertEqual(
            event.details["exception_type"],
            "RuntimeError",
        )

    def test_routing_failure_is_classified_separately(
        self,
    ):

        error = ValueError(
            "No valid transition"
        )

        event = (
            WorkflowExecutionEventService
            .record_failure(
                instance=self.instance,
                event=(
                    WorkflowExecutionEventService
                    .TRANSITION_REJECTED
                ),
                exception=error,
            )
        )

        self.assertEqual(
            event.details["failure_type"],
            (
                WorkflowExecutionEventService
                .FAILURE_TYPE_ROUTING
            ),
        )

        self.assertEqual(
            event.details["failure_stage"],
            (
                WorkflowExecutionEventService
                .FAILURE_STAGE_ROUTING
            ),
        )

    def test_runtime_failure_is_classified_separately(
        self,
    ):

        error = RuntimeError(
            "Runtime failure"
        )

        event = (
            WorkflowExecutionEventService
            .record_failure(
                instance=self.instance,
                event=(
                    WorkflowExecutionEventService
                    .WORKFLOW_FAILED
                ),
                exception=error,
            )
        )

        self.assertEqual(
            event.details["failure_type"],
            (
                WorkflowExecutionEventService
                .FAILURE_TYPE_RUNTIME
            ),
        )

        self.assertEqual(
            event.details["failure_stage"],
            (
                WorkflowExecutionEventService
                .FAILURE_STAGE_RUNTIME
            ),
        )

    def test_failure_event_retains_authoritative_identity(
        self,
    ):

        error = RuntimeError(
            "failure"
        )

        event = (
            WorkflowExecutionEventService
            .record_failure(
                instance=self.instance,
                event=(
                    WorkflowExecutionEventService
                    .NODE_FAILED
                ),
                exception=error,
                details={
                    "correlation_id": "fake",
                    "workflow_id": "fake",
                    "workflow_version": 999,
                },
            )
        )

        self.assertEqual(
            event.details["correlation_id"],
            str(self.instance.pk),
        )

        self.assertEqual(
            event.details["workflow_id"],
            str(self.workflow.pk),
        )

        self.assertEqual(
            event.details["workflow_version"],
            self.workflow.version,
        )

        self.assertEqual(
            WorkflowExecutionLog.objects.count(),
            1,
        )