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

from workflow.services.runtime_lifecycle import (
    WorkflowRuntimeLifecycleService,
)


User = get_user_model()


class WorkflowRuntimeLifecycleIntegrityTests(
    TestCase
):

    def setUp(self):

        self.organization = (
            Organization.objects.create(
                name="Lifecycle Integrity Organization",
                slug="lifecycle-integrity-organization",
            )
        )

        self.user = User.objects.create_user(
            email="lifecycle-integrity@example.com",
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
                name="Lifecycle Integrity Workflow",
                code="LIFECYCLE_INTEGRITY_WORKFLOW",
                version=1,
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

    def test_cancel_persists_state_and_event_atomically(
        self,
    ):

        result = (
            WorkflowRuntimeLifecycleService.cancel(
                self.instance,
                actor=self.user,
                actor_type="user",
                source="runtime_api",
            )
        )

        self.assertEqual(
            result.status,
            WorkflowInstance.STATUS_CANCELLED,
        )

        self.assertIsNotNone(
            result.completed_at
        )

        event = (
            WorkflowExecutionLog.objects.get(
                instance=self.instance,
                event=(
                    "workflow_cancelled"
                ),
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

    def test_complete_persists_state_and_event_atomically(
        self,
    ):

        result = (
            WorkflowRuntimeLifecycleService.complete(
                self.instance,
                actor=self.user,
                actor_type="user",
                source="runtime_api",
            )
        )

        self.assertEqual(
            result.status,
            WorkflowInstance.STATUS_COMPLETED,
        )

        self.assertIsNotNone(
            result.completed_at
        )

        event = (
            WorkflowExecutionLog.objects.get(
                instance=self.instance,
                event=(
                    "workflow_completed"
                ),
            )
        )

        self.assertEqual(
            event.details["correlation_id"],
            str(self.instance.pk),
        )

    def test_fail_persists_state_and_event_atomically(
        self,
    ):

        result = (
            WorkflowRuntimeLifecycleService.fail(
                self.instance,
                error_type="ValidationError",
                error_message="Workflow graph is invalid.",
                actor=self.user,
                actor_type="user",
                source="runtime_api",
            )
        )

        self.assertEqual(
            result.status,
            WorkflowInstance.STATUS_FAILED,
        )

        self.assertIsNotNone(
            result.completed_at
        )

        event = (
            WorkflowExecutionLog.objects.get(
                instance=self.instance,
                event=(
                    "workflow_failed"
                ),
            )
        )

        self.assertEqual(
            event.details["error_type"],
            "ValidationError",
        )

        self.assertEqual(
            event.details["error_message"],
            "Workflow graph is invalid.",
        )

        self.assertEqual(
            event.details["correlation_id"],
            str(self.instance.pk),
        )

    def test_cancel_is_idempotent(
        self,
    ):

        first = (
            WorkflowRuntimeLifecycleService.cancel(
                self.instance,
                actor=self.user,
                actor_type="user",
                source="runtime_api",
            )
        )

        first_completed_at = (
            first.completed_at
        )

        first_event_count = (
            WorkflowExecutionLog.objects.filter(
                instance=self.instance,
                event="workflow_cancelled",
            ).count()
        )

        second = (
            WorkflowRuntimeLifecycleService.cancel(
                self.instance,
                actor=self.user,
                actor_type="user",
                source="runtime_api",
            )
        )

        self.assertEqual(
            second.status,
            WorkflowInstance.STATUS_CANCELLED,
        )

        self.assertEqual(
            second.completed_at,
            first_completed_at,
        )

        self.assertEqual(
            WorkflowExecutionLog.objects.filter(
                instance=self.instance,
                event="workflow_cancelled",
            ).count(),
            first_event_count,
        )

    def test_completed_instance_cannot_be_failed(
        self,
    ):

        self.instance.status = (
            WorkflowInstance.STATUS_COMPLETED
        )

        self.instance.save(
            update_fields=[
                "status",
            ]
        )

        WorkflowRuntimeLifecycleService.fail(
            self.instance,
            error_type="UnexpectedError",
            error_message="Should not mutate terminal state.",
        )

        self.instance.refresh_from_db()

        self.assertEqual(
            self.instance.status,
            WorkflowInstance.STATUS_COMPLETED,
        )

        self.assertFalse(
            WorkflowExecutionLog.objects.filter(
                instance=self.instance,
                event="workflow_failed",
            ).exists()
        )

    def test_cancelled_instance_cannot_be_completed(
        self,
    ):

        self.instance.status = (
            WorkflowInstance.STATUS_CANCELLED
        )

        self.instance.save(
            update_fields=[
                "status",
            ]
        )

        WorkflowRuntimeLifecycleService.complete(
            self.instance
        )

        self.instance.refresh_from_db()

        self.assertEqual(
            self.instance.status,
            WorkflowInstance.STATUS_CANCELLED,
        )

        self.assertFalse(
            WorkflowExecutionLog.objects.filter(
                instance=self.instance,
                event="workflow_completed",
            ).exists()
        )

    def test_failed_instance_cannot_be_cancelled(
        self,
    ):

        self.instance.status = (
            WorkflowInstance.STATUS_FAILED
        )

        self.instance.save(
            update_fields=[
                "status",
            ]
        )

        WorkflowRuntimeLifecycleService.cancel(
            self.instance
        )

        self.instance.refresh_from_db()

        self.assertEqual(
            self.instance.status,
            WorkflowInstance.STATUS_FAILED,
        )

        self.assertFalse(
            WorkflowExecutionLog.objects.filter(
                instance=self.instance,
                event="workflow_cancelled",
            ).exists()
        )