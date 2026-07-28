from django.test import TestCase

from workflow.models import (
    WorkflowNode,
    WorkflowTransition,
    WorkflowInstance,
)

from workflow.services.runtime_engine import (
    WorkflowRuntimeEngine,
)

from workflow.tests.utils import create_workflow


class WorkflowRuntimeEngineTests(TestCase):

    def test_run_linear_workflow(self):

        workflow = create_workflow()

        start = WorkflowNode.objects.create(
            workflow=workflow,
            name="Start",
            node_type=WorkflowNode.START,
        )

        end = WorkflowNode.objects.create(
            workflow=workflow,
            name="End",
            node_type=WorkflowNode.END,
        )

        WorkflowTransition.objects.create(
            workflow=workflow,
            source=start,
            target=end,
        )

        instance = WorkflowInstance.objects.create(
            workflow=workflow,
            organization=workflow.organization,
        )

        engine = WorkflowRuntimeEngine(
            instance
        )

        engine.run()

        instance.refresh_from_db()

        self.assertEqual(
            instance.status,
            WorkflowInstance.STATUS_COMPLETED,
        )

    def test_context_is_saved(self):

        workflow = create_workflow()

        start = WorkflowNode.objects.create(
            workflow=workflow,
            name="Start",
            node_type=WorkflowNode.START,
        )

        end = WorkflowNode.objects.create(
            workflow=workflow,
            name="End",
            node_type=WorkflowNode.END,
        )

        WorkflowTransition.objects.create(
            workflow=workflow,
            source=start,
            target=end,
        )

        instance = WorkflowInstance.objects.create(
            workflow=workflow,
            organization=workflow.organization,
        )

        WorkflowRuntimeEngine(
            instance
        ).run()

        instance.refresh_from_db()

        self.assertTrue(
            instance.context["_started"]
        )