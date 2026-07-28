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