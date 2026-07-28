from django.db import IntegrityError
from django.test import TestCase

from workflow.models import (
    WorkflowDefinition,
    WorkflowNode,
    WorkflowTransition,
    WorkflowVariable,
)

from workflow.tests.utils import create_workflow


class WorkflowModelTests(TestCase):

    def test_create_workflow(self):

        workflow = create_workflow()

        self.assertIsInstance(
            workflow,
            WorkflowDefinition,
        )

    def test_create_node(self):

        workflow = create_workflow()

        node = WorkflowNode.objects.create(
            workflow=workflow,
            name="Start",
            node_type=WorkflowNode.START,
        )

        self.assertEqual(
            node.workflow,
            workflow,
        )

    def test_create_variable(self):

        workflow = create_workflow()

        variable = WorkflowVariable.objects.create(
            workflow=workflow,
            name="customer_name",
        )

        self.assertEqual(
            variable.name,
            "customer_name",
        )

    def test_duplicate_variable(self):

        workflow = create_workflow()

        WorkflowVariable.objects.create(
            workflow=workflow,
            name="status",
        )

        with self.assertRaises(
            IntegrityError
        ):

            WorkflowVariable.objects.create(
                workflow=workflow,
                name="status",
            )

    def test_transition_creation(self):

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

        transition = WorkflowTransition.objects.create(
            workflow=workflow,
            source=start,
            target=end,
        )

        self.assertEqual(
            transition.source,
            start,
        )