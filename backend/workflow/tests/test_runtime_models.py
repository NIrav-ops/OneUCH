from django.test import TestCase

from workflow.models import (
    WorkflowInstance,
    WorkflowNode,
    WorkflowToken,
    WorkflowExecutionLog,
)

from workflow.tests.utils import create_workflow


class WorkflowRuntimeModelTests(TestCase):

    def test_create_instance(self):

        workflow = create_workflow()

        instance = WorkflowInstance.objects.create(
            workflow=workflow,
            organization=workflow.organization,
            started_by=workflow.created_by,
        )

        self.assertEqual(
            instance.status,
            WorkflowInstance.STATUS_RUNNING,
        )

    def test_create_token(self):

        workflow = create_workflow()

        node = WorkflowNode.objects.create(
            workflow=workflow,
            name="Start",
            node_type=WorkflowNode.START,
        )

        instance = WorkflowInstance.objects.create(
            workflow=workflow,
            organization=workflow.organization,
        )

        token = WorkflowToken.objects.create(
            instance=instance,
            node=node,
        )

        self.assertEqual(
            token.status,
            WorkflowToken.STATUS_ACTIVE,
        )

    def test_execution_log(self):

        workflow = create_workflow()

        instance = WorkflowInstance.objects.create(
            workflow=workflow,
            organization=workflow.organization,
        )

        log = WorkflowExecutionLog.objects.create(
            instance=instance,
            event="Workflow Started",
        )

        self.assertEqual(
            log.event,
            "Workflow Started",
        )