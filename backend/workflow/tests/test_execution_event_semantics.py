from django.contrib.auth import get_user_model
from django.test import TestCase

from inbox.models import (
    Organization,
    OrganizationUser,
)

from workflow.models import (
    WorkflowDefinition,
    WorkflowExecutionLog,
    WorkflowInstance,
)

from workflow.services.execution.events import (
    WorkflowExecutionEventService,
)


User = get_user_model()


class WorkflowExecutionEventSemanticsTests(
    TestCase
):

    def setUp(self):

        self.organization = (
            Organization.objects.create(
                name="Event Semantics Organization",
                slug="event-semantics-organization",
            )
        )

        self.user = User.objects.create_user(
            email="event-semantics@example.com",
            password="test-password",
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=self.organization,
            role="member",
        )

        self.workflow = (
            WorkflowDefinition.objects.create(
                organization=self.organization,
                name="Event Semantics Workflow",
                code="EVENT_SEMANTICS_WORKFLOW",
                version=4,
                status=(
                    WorkflowDefinition.STATUS_ACTIVE
                ),
            )
        )

        self.instance = (
            WorkflowInstance.objects.create(
                workflow=self.workflow,
                organization=self.organization,
                started_by=self.user,
                context={},
            )
        )

    def test_workflow_started_is_classified_as_success(self):

        event = (
            WorkflowExecutionEventService.record(
                instance=self.instance,
                event=(
                    WorkflowExecutionEventService
                    .WORKFLOW_STARTED
                ),
                actor=self.user,
                actor_type="user",
                source="runtime_api",
            )
        )

        self.assertEqual(
            event.details["event_category"],
            "workflow",
        )

        self.assertEqual(
            event.details["event_result"],
            "success",
        )

        self.assertFalse(
            event.details["event_terminal"]
        )

    def test_workflow_completed_is_terminal(self):

        event = (
            WorkflowExecutionEventService.record(
                instance=self.instance,
                event=(
                    WorkflowExecutionEventService
                    .WORKFLOW_COMPLETED
                ),
            )
        )

        self.assertEqual(
            event.details["event_category"],
            "workflow",
        )

        self.assertEqual(
            event.details["event_result"],
            "success",
        )

        self.assertTrue(
            event.details["event_terminal"]
        )

    def test_node_failed_is_failure_event(self):

        event = (
            WorkflowExecutionEventService.record(
                instance=self.instance,
                event=(
                    WorkflowExecutionEventService
                    .NODE_FAILED
                ),
            )
        )

        self.assertEqual(
            event.details["event_category"],
            "node",
        )

        self.assertEqual(
            event.details["event_result"],
            "failure",
        )

        self.assertFalse(
            event.details["event_terminal"]
        )

    def test_transition_selected_is_routing_success(self):

        event = (
            WorkflowExecutionEventService.record(
                instance=self.instance,
                event=(
                    WorkflowExecutionEventService
                    .TRANSITION_SELECTED
                ),
            )
        )

        self.assertEqual(
            event.details["event_category"],
            "routing",
        )

        self.assertEqual(
            event.details["event_result"],
            "success",
        )

    def test_transition_rejected_is_routing_failure(self):

        event = (
            WorkflowExecutionEventService.record(
                instance=self.instance,
                event=(
                    WorkflowExecutionEventService
                    .TRANSITION_REJECTED
                ),
            )
        )

        self.assertEqual(
            event.details["event_category"],
            "routing",
        )

        self.assertEqual(
            event.details["event_result"],
            "failure",
        )

    def test_caller_cannot_override_event_semantics(self):

        event = (
            WorkflowExecutionEventService.record(
                instance=self.instance,
                event=(
                    WorkflowExecutionEventService
                    .NODE_FAILED
                ),
                details={
                    "event_category": "workflow",
                    "event_result": "success",
                    "event_terminal": True,
                },
            )
        )

        self.assertEqual(
            event.details["event_category"],
            "node",
        )

        self.assertEqual(
            event.details["event_result"],
            "failure",
        )

        self.assertFalse(
            event.details["event_terminal"]
        )

    def test_caller_cannot_override_workflow_identity(self):

        event = (
            WorkflowExecutionEventService.record(
                instance=self.instance,
                event=(
                    WorkflowExecutionEventService
                    .WORKFLOW_STARTED
                ),
                details={
                    "workflow_id": "malicious-workflow",
                    "workflow_version": 999,
                    "workflow_code": "FAKE",
                },
            )
        )

        self.assertEqual(
            event.details["workflow_id"],
            str(self.workflow.pk),
        )

        self.assertEqual(
            event.details["workflow_version"],
            4,
        )

        self.assertEqual(
            event.details["workflow_code"],
            "EVENT_SEMANTICS_WORKFLOW",
        )

    def test_caller_cannot_override_correlation_id(self):

        event = (
            WorkflowExecutionEventService.record(
                instance=self.instance,
                event=(
                    WorkflowExecutionEventService
                    .WORKFLOW_STARTED
                ),
                details={
                    "correlation_id": (
                        "malicious-correlation"
                    ),
                },
            )
        )

        self.assertEqual(
            event.details["correlation_id"],
            str(self.instance.pk),
        )

    def test_unknown_event_is_rejected(self):

        with self.assertRaises(ValueError):

            WorkflowExecutionEventService.record(
                instance=self.instance,
                event="unknown_execution_event",
            )

        self.assertFalse(
            WorkflowExecutionLog.objects.filter(
                instance=self.instance,
            ).exists()
        )

    def test_node_failure_has_failure_result(
        self,
    ):

        event = (
            WorkflowExecutionEventService
            .record_failure(
                instance=self.instance,
                event=(
                    WorkflowExecutionEventService
                    .NODE_FAILED
                ),
                exception=RuntimeError(
                    "failure"
                ),
            )
        )

        self.assertEqual(
            event.details["event_category"],
            "node",
        )

        self.assertEqual(
            event.details["event_result"],
            "failure",
        )

        self.assertFalse(
            event.details["event_terminal"]
        )

        self.assertEqual(
            event.details["failure_type"],
            (
                WorkflowExecutionEventService
                .FAILURE_TYPE_NODE_EXECUTION
            ),
        )