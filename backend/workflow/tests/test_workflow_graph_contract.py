from django.test import TestCase

from inbox.models import Organization

from workflow.models import (
    WorkflowDefinition,
    WorkflowNode,
    WorkflowTransition,
)

from workflow.services.builder.graph_service import (
    WorkflowGraphService,
)


class WorkflowGraphContractTests(
    TestCase
):

    def setUp(self):

        self.organization = (
            Organization.objects.create(
                name="Graph Contract Organization",
                slug="graph-contract-organization",
            )
        )

        self.workflow = (
            WorkflowDefinition.objects.create(
                organization=self.organization,
                name="Contract Workflow",
                code="CONTRACT_WORKFLOW",
                description="Designer contract test",
                version=3,
                status=(
                    WorkflowDefinition.STATUS_DRAFT
                ),
            )
        )

        self.start = (
            WorkflowNode.objects.create(
                workflow=self.workflow,
                name="Start",
                node_type=WorkflowNode.START,
                configuration={},
                position_x=100,
                position_y=200,
            )
        )

        self.end = (
            WorkflowNode.objects.create(
                workflow=self.workflow,
                name="End",
                node_type=WorkflowNode.END,
                configuration={},
                position_x=400,
                position_y=200,
            )
        )

        self.transition = (
            WorkflowTransition.objects.create(
                workflow=self.workflow,
                source=self.start,
                target=self.end,
                condition="",
                priority=100,
            )
        )

        self.service = (
            WorkflowGraphService()
        )

    def test_graph_exposes_workflow_runtime_state(
        self,
    ):

        result = self.service.get_graph(
            workflow=self.workflow
        )

        self.assertEqual(
            result["workflow"],
            str(self.workflow.pk),
        )

        self.assertEqual(
            result["workflow_code"],
            "CONTRACT_WORKFLOW",
        )

        self.assertEqual(
            result["workflow_name"],
            "Contract Workflow",
        )

        self.assertEqual(
            result["workflow_version"],
            3,
        )

        self.assertEqual(
            result["workflow_status"],
            WorkflowDefinition.STATUS_DRAFT,
        )

        self.assertTrue(
            result["editable"]
        )

    def test_graph_exposes_persisted_node_identity(
        self,
    ):

        result = self.service.get_graph(
            workflow=self.workflow
        )

        nodes = result["nodes"]

        self.assertEqual(
            len(nodes),
            2,
        )

        for node in nodes:

            self.assertIn(
                "id",
                node,
            )

            self.assertIn(
                "client_id",
                node,
            )

            self.assertEqual(
                node["id"],
                node["client_id"],
            )

    def test_graph_exposes_transition_identity(
        self,
    ):

        result = self.service.get_graph(
            workflow=self.workflow
        )

        transitions = (
            result["transitions"]
        )

        self.assertEqual(
            len(transitions),
            1,
        )

        transition = transitions[0]

        self.assertIn(
            "id",
            transition,
        )

        self.assertEqual(
            transition["source"],
            str(self.start.pk),
        )

        self.assertEqual(
            transition["target"],
            str(self.end.pk),
        )

    def test_active_workflow_is_not_editable(
        self,
    ):

        self.workflow.status = (
            WorkflowDefinition.STATUS_ACTIVE
        )

        self.workflow.save(
            update_fields=[
                "status",
            ]
        )

        result = self.service.get_graph(
            workflow=self.workflow
        )

        self.assertEqual(
            result["workflow_status"],
            WorkflowDefinition.STATUS_ACTIVE,
        )

        self.assertFalse(
            result["editable"]
        )

    def test_archived_workflow_is_not_editable(
        self,
    ):

        self.workflow.status = (
            WorkflowDefinition.STATUS_ARCHIVED
        )

        self.workflow.save(
            update_fields=[
                "status",
            ]
        )

        result = self.service.get_graph(
            workflow=self.workflow
        )

        self.assertEqual(
            result["workflow_status"],
            WorkflowDefinition.STATUS_ARCHIVED,
        )

        self.assertFalse(
            result["editable"]
        )