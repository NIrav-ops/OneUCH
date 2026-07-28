from django.test import TestCase

from workflow.models import (
    WorkflowNode,
    WorkflowInstance,
    WorkflowToken,
)

from workflow.services.context import (
    WorkflowExecutionContext,
)

from workflow.services.executors.factory import (
    ExecutorFactory,
)

from workflow.tests.utils import create_workflow


class WorkflowExecutorTests(TestCase):

    def test_start_executor(self):

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

        context = WorkflowExecutionContext(
            instance
        )

        executor_cls = ExecutorFactory.get_executor(
            node.node_type
        )

        executor = executor_cls(
            context,
            token,
        )

        self.assertTrue(
            executor.execute()
        )

        self.assertTrue(
            context.get("_started")
        )

    def test_end_executor(self):

        workflow = create_workflow()

        node = WorkflowNode.objects.create(
            workflow=workflow,
            name="End",
            node_type=WorkflowNode.END,
        )

        instance = WorkflowInstance.objects.create(
            workflow=workflow,
            organization=workflow.organization,
        )

        token = WorkflowToken.objects.create(
            instance=instance,
            node=node,
        )

        context = WorkflowExecutionContext(
            instance
        )

        executor_cls = ExecutorFactory.get_executor(
            node.node_type
        )

        executor = executor_cls(
            context,
            token,
        )

        executor.execute()

        instance.refresh_from_db()

        self.assertEqual(
            instance.status,
            WorkflowInstance.STATUS_COMPLETED,
        )

    def test_unknown_executor(self):

        with self.assertRaises(
            ValueError
        ):

            ExecutorFactory.get_executor(
                "invalid_node"
            )