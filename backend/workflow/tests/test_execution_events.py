from django.test import TestCase

from workflow.models import (
    WorkflowExecutionLog,
    WorkflowInstance,
)

from workflow.services.execution import (
    WorkflowExecutionEventService,
)

from workflow.tests.utils import (
    create_workflow,
)


class WorkflowExecutionEventTests(TestCase):

    def test_records_execution_event(self):

        workflow = create_workflow()

        instance = WorkflowInstance.objects.create(
            workflow=workflow,
            organization=workflow.organization,
        )

        WorkflowExecutionEventService.record(
            instance=instance,
            event=WorkflowExecutionEventService.WORKFLOW_STARTED,
        )

        self.assertEqual(
            WorkflowExecutionLog.objects.count(),
            1,
        )

        log = WorkflowExecutionLog.objects.first()

        self.assertEqual(
            log.instance,
            instance,
        )

        self.assertEqual(
            log.event,
            WorkflowExecutionEventService.WORKFLOW_STARTED,
        )

    def test_records_actor_and_source_metadata(self):

        workflow = create_workflow()

        instance = WorkflowInstance.objects.create(
            workflow=workflow,
            organization=workflow.organization,
        )

        user = workflow.created_by

        WorkflowExecutionEventService.record(
            instance=instance,
            event=(
                WorkflowExecutionEventService.WORKFLOW_STARTED
            ),
            actor=user,
            actor_type="user",
            source="runtime_api",
        )

        log = WorkflowExecutionLog.objects.first()

        self.assertEqual(
            log.details["actor_type"],
            "user",
        )

        self.assertEqual(
            log.details["actor_id"],
            str(user.pk),
        )

        self.assertEqual(
            log.details["source"],
            "runtime_api",
        )

        self.assertEqual(
            log.details["workflow_version"],
            workflow.version,
        )

        self.assertEqual(
            log.details["workflow_id"],
            str(workflow.pk),
        )

    def test_event_contains_execution_identity(self):

        workflow = create_workflow()

        instance = WorkflowInstance.objects.create(
            workflow=workflow,
            organization=workflow.organization,
            started_by=workflow.created_by,
            context={},
        )

        event = WorkflowExecutionEventService.record(
            instance=instance,
            event=(
                WorkflowExecutionEventService
                .WORKFLOW_STARTED
            ),
        )

        self.assertEqual(
            event.details["workflow_id"],
            str(workflow.pk),
        )

        self.assertEqual(
            event.details["workflow_version"],
            workflow.version,
        )

        self.assertEqual(
            event.details["workflow_code"],
            workflow.code,
        )

        self.assertEqual(
            event.details["started_by"],
            str(workflow.created_by.pk),
        )

        self.assertEqual(
            event.details["started_by_email"],
            workflow.created_by.email,
        )

    def test_event_allows_system_execution_without_started_by(self):

        workflow = create_workflow()

        instance = WorkflowInstance.objects.create(
            workflow=workflow,
            organization=workflow.organization,
            started_by=None,
            context={},
        )

        event = WorkflowExecutionEventService.record(
            instance=instance,
            event=(
                WorkflowExecutionEventService
                .WORKFLOW_STARTED
            ),
        )

        self.assertIsNone(
            event.details["started_by"]
        )

        self.assertIsNone(
            event.details["started_by_email"]
        )