from django.test import TestCase

from workflow.models import (
    WorkflowNode,
    WorkflowTransition,
)

from workflow.services.validator import (
    WorkflowValidationError,
    WorkflowValidator,
)

from workflow.tests.utils import create_workflow


class WorkflowValidatorTests(TestCase):

    def test_valid_node(self):

        workflow = create_workflow()

        node = WorkflowNode.objects.create(
            workflow=workflow,
            name="Start",
            node_type=WorkflowNode.START,
        )

        self.assertTrue(
            WorkflowValidator.validate_node(
                node
            )
        )

    def test_invalid_transition(self):

        workflow = create_workflow()

        node = WorkflowNode.objects.create(
            workflow=workflow,
            name="Start",
            node_type=WorkflowNode.START,
        )

        transition = WorkflowTransition.objects.create(
            workflow=workflow,
            source=node,
            target=node,
        )

        with self.assertRaises(
            WorkflowValidationError
        ):

            WorkflowValidator.validate_transition(
                transition
            )

    def test_valid_workflow(self):

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

        self.assertTrue(
            WorkflowValidator.validate_workflow(
                workflow
            )
        )

    def test_missing_end_node(self):

        workflow = create_workflow()

        WorkflowNode.objects.create(
            workflow=workflow,
            name="Start",
            node_type=WorkflowNode.START,
        )

        with self.assertRaises(
            WorkflowValidationError
        ):

            WorkflowValidator.validate_workflow(
                workflow
            )

    def test_multiple_start_nodes(self):

        workflow = create_workflow()

        WorkflowNode.objects.create(
            workflow=workflow,
            name="Start1",
            node_type=WorkflowNode.START,
        )

        WorkflowNode.objects.create(
            workflow=workflow,
            name="Start2",
            node_type=WorkflowNode.START,
        )

        WorkflowNode.objects.create(
            workflow=workflow,
            name="End",
            node_type=WorkflowNode.END,
        )

        with self.assertRaises(
            WorkflowValidationError
        ):

            WorkflowValidator.validate_workflow(
                workflow
            )