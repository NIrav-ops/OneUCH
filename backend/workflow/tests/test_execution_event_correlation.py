from django.contrib.auth import get_user_model
from django.test import TestCase

from inbox.models import (
    Organization,
    OrganizationUser,
)

from workflow.models import (
    WorkflowDefinition,
    WorkflowInstance,
    WorkflowExecutionLog,
)

from workflow.services.execution import (
    WorkflowExecutionEventService,
)


User = get_user_model()


class WorkflowExecutionEventCorrelationTests(
    TestCase
):

    def setUp(self):

        self.organization = (
            Organization.objects.create(
                name="Execution Correlation Organization",
                slug="execution-correlation-organization",
            )
        )

        self.user = User.objects.create_user(
            email="execution-correlation@example.com",
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
                name="Execution Correlation Workflow",
                code="EXECUTION_CORRELATION",
                version=2,
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

    def test_event_contains_instance_correlation_id(
        self,
    ):

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
            event.details["correlation_id"],
            str(self.instance.pk),
        )

    def test_all_events_for_instance_share_correlation_id(
        self,
    ):

        first_event = (
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

        second_event = (
            WorkflowExecutionEventService.record(
                instance=self.instance,
                event=(
                    WorkflowExecutionEventService
                    .WORKFLOW_COMPLETED
                ),
                actor=self.user,
                actor_type="user",
                source="runtime_api",
            )
        )

        self.assertEqual(
            first_event.details["correlation_id"],
            second_event.details["correlation_id"],
        )

        self.assertEqual(
            first_event.details["correlation_id"],
            str(self.instance.pk),
        )

    def test_caller_cannot_override_correlation_id(
        self,
    ):

        event = (
            WorkflowExecutionEventService.record(
                instance=self.instance,
                event=(
                    WorkflowExecutionEventService
                    .WORKFLOW_STARTED
                ),
                details={
                    "correlation_id": (
                        "malicious-or-invalid-correlation-id"
                    ),
                },
                actor=self.user,
                actor_type="user",
                source="runtime_api",
            )
        )

        self.assertEqual(
            event.details["correlation_id"],
            str(self.instance.pk),
        )

    def test_correlation_id_is_stable_for_same_instance(
        self,
    ):

        first_event = (
            WorkflowExecutionEventService.record(
                instance=self.instance,
                event=(
                    WorkflowExecutionEventService
                    .WORKFLOW_STARTED
                ),
            )
        )

        second_event = (
            WorkflowExecutionEventService.record(
                instance=self.instance,
                event=(
                    WorkflowExecutionEventService
                    .WORKFLOW_SUSPENDED
                ),
            )
        )

        third_event = (
            WorkflowExecutionEventService.record(
                instance=self.instance,
                event=(
                    WorkflowExecutionEventService
                    .WORKFLOW_RESUMED
                ),
            )
        )

        correlation_ids = {
            first_event.details["correlation_id"],
            second_event.details["correlation_id"],
            third_event.details["correlation_id"],
        }

        self.assertEqual(
            len(correlation_ids),
            1,
        )

        self.assertEqual(
            correlation_ids.pop(),
            str(self.instance.pk),
        )

    def test_different_instances_have_different_correlation_ids(
        self,
    ):

        second_instance = (
            WorkflowInstance.objects.create(
                workflow=self.workflow,
                organization=self.organization,
                started_by=self.user,
                context={},
            )
        )

        first_event = (
            WorkflowExecutionEventService.record(
                instance=self.instance,
                event=(
                    WorkflowExecutionEventService
                    .WORKFLOW_STARTED
                ),
            )
        )

        second_event = (
            WorkflowExecutionEventService.record(
                instance=second_instance,
                event=(
                    WorkflowExecutionEventService
                    .WORKFLOW_STARTED
                ),
            )
        )

        self.assertNotEqual(
            first_event.details["correlation_id"],
            second_event.details["correlation_id"],
        )