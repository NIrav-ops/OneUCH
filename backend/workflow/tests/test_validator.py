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

    def test_unreachable_node_is_rejected(
        self,
    ):

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

        WorkflowNode.objects.create(
            workflow=workflow,
            name="Orphan Action",
            node_type=WorkflowNode.ACTION,
        )

        WorkflowTransition.objects.create(
            workflow=workflow,
            source=start,
            target=end,
        )

        with self.assertRaisesMessage(
            WorkflowValidationError,
            "Workflow contains unreachable nodes: Orphan Action.",
        ):

            WorkflowValidator.validate_workflow(
                workflow
            )


    def test_unreachable_end_is_rejected(
        self,
    ):

        workflow = create_workflow()

        start = WorkflowNode.objects.create(
            workflow=workflow,
            name="Start",
            node_type=WorkflowNode.START,
        )

        WorkflowNode.objects.create(
            workflow=workflow,
            name="Reachable Action",
            node_type=WorkflowNode.ACTION,
        )

        WorkflowNode.objects.create(
            workflow=workflow,
            name="Unreachable End",
            node_type=WorkflowNode.END,
        )

    #
    # No transition from START.
    #
    # The existing graph therefore cannot reach
    # the END node.
    #

        with self.assertRaisesMessage(
            WorkflowValidationError,
            "Workflow contains unreachable nodes:",
        ):

            WorkflowValidator.validate_workflow(
                workflow
            )


    def test_all_nodes_reachable_is_valid(
        self,
    ):

        workflow = create_workflow()

        start = WorkflowNode.objects.create(
            workflow=workflow,
            name="Start",
            node_type=WorkflowNode.START,
        )

        action = WorkflowNode.objects.create(
            workflow=workflow,
            name="Action",
            node_type=WorkflowNode.ACTION,
        )

        end = WorkflowNode.objects.create(
            workflow=workflow,
            name="End",
            node_type=WorkflowNode.END,
        )

        WorkflowTransition.objects.create(
            workflow=workflow,
            source=start,
            target=action,
        )

        WorkflowTransition.objects.create(
            workflow=workflow,
            source=action,
            target=end,
        )

        self.assertTrue(
            WorkflowValidator.validate_workflow(
                workflow
            )
        )

    def test_start_node_cannot_have_incoming_transition(
        self,
    ):

        workflow = create_workflow()

        start = WorkflowNode.objects.create(
            workflow=workflow,
            name="Start",
            node_type=WorkflowNode.START,
        )

        action = WorkflowNode.objects.create(
            workflow=workflow,
            name="Action",
            node_type=WorkflowNode.ACTION,
        )

        end = WorkflowNode.objects.create(
            workflow=workflow,
            name="End",
            node_type=WorkflowNode.END,
        )

        WorkflowTransition.objects.create(
            workflow=workflow,
            source=start,
            target=action,
        )

        WorkflowTransition.objects.create(
            workflow=workflow,
            source=action,
            target=start,
        )

        WorkflowTransition.objects.create(
            workflow=workflow,
            source=action,
            target=end,
        )

        with self.assertRaisesMessage(
            WorkflowValidationError,
            "START node cannot have incoming transitions.",
        ):

            WorkflowValidator.validate_workflow(
                workflow
            )


    def test_end_node_cannot_have_outgoing_transition(
        self,
    ):

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

        action = WorkflowNode.objects.create(
            workflow=workflow,
            name="After End",
            node_type=WorkflowNode.ACTION,
        )

        WorkflowTransition.objects.create(
            workflow=workflow,
            source=start,
            target=end,
        )

        WorkflowTransition.objects.create(
            workflow=workflow,
            source=end,
            target=action,
        )

        with self.assertRaisesMessage(
            WorkflowValidationError,
            "END node cannot have outgoing transitions.",
        ):

            WorkflowValidator.validate_workflow(
                workflow
            )

    def test_non_end_node_requires_outgoing_transition(
        self,
    ):

        workflow = create_workflow()

        start = WorkflowNode.objects.create(
            workflow=workflow,
            name="Start",
            node_type=WorkflowNode.START,
        )

        action = WorkflowNode.objects.create(
            workflow=workflow,
            name="Action",
            node_type=WorkflowNode.ACTION,
        )

        end = WorkflowNode.objects.create(
            workflow=workflow,
            name="End",
            node_type=WorkflowNode.END,
        )

        #
        # Both ACTION and END are reachable from START.
        #
        # ACTION intentionally has no outgoing transition.
        #

        WorkflowTransition.objects.create(
            workflow=workflow,
            source=start,
            target=action,
        )

        WorkflowTransition.objects.create(
            workflow=workflow,
            source=start,
            target=end,
        )

        with self.assertRaisesMessage(
            WorkflowValidationError,
            "Node 'Action' has no outgoing transition.",
        ):

            WorkflowValidator.validate_workflow(
                workflow
            )