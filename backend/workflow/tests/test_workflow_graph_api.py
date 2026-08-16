import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework.test import APIClient

from inbox.models import (
    Organization,
    OrganizationUser,
)

from workflow.models import (
    WorkflowDefinition,
    WorkflowNode,
    WorkflowTransition,
)


User = get_user_model()


class WorkflowGraphAPITests(
    TestCase
):

    def setUp(self):

        self.organization = (
            Organization.objects.create(
                name="Graph API Organization",
                slug="graph-api-organization",
            )
        )

        self.other_organization = (
            Organization.objects.create(
                name="Other Graph Organization",
                slug="other-graph-organization",
            )
        )

        self.user = User.objects.create_user(
            email="graph-api@example.com",
            password="test-password",
        )

        self.client = APIClient()

        self.client.force_authenticate(
            user=self.user
        )

        self.workflow = (
            WorkflowDefinition.objects.create(
                organization=self.organization,
                name="Graph Workflow",
                code="GRAPH_WORKFLOW",
                status=(
                    WorkflowDefinition.STATUS_DRAFT
                ),
            )
        )

    def _attach_organization(self):

        OrganizationUser.objects.update_or_create(
            user=self.user,
            defaults={
                "organization": self.organization,
                "role": "member",
            },
        )

    def test_get_graph_returns_nodes_and_transitions(
        self,
    ):

        self._attach_organization()

        start = WorkflowNode.objects.create(
            workflow=self.workflow,
            name="Start",
            node_type=WorkflowNode.START,
            configuration={},
            position_x=100,
            position_y=200,
        )

        end = WorkflowNode.objects.create(
            workflow=self.workflow,
            name="End",
            node_type=WorkflowNode.END,
            configuration={},
            position_x=300,
            position_y=200,
        )

        WorkflowTransition.objects.create(
            workflow=self.workflow,
            source=start,
            target=end,
            priority=100,
            condition="",
        )

        response = self.client.get(
            "/api/workflow/builder/graph/",
            {
                "workflow": str(
                    self.workflow.pk
                )
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["workflow"],
            str(self.workflow.pk),
        )

        self.assertEqual(
            len(response.data["nodes"]),
            2,
        )

        self.assertEqual(
            len(response.data["transitions"]),
            1,
        )

        transition = (
            response.data[
                "transitions"
            ][0]
        )

        self.assertEqual(
            transition["source"],
            str(start.pk),
        )

        self.assertEqual(
            transition["target"],
            str(end.pk),
        )

    def test_missing_workflow_returns_404(
        self,
    ):

        self._attach_organization()

        response = self.client.get(
            "/api/workflow/builder/graph/",
            {
                "workflow": str(
                    uuid.uuid4()
                )
            },
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_other_organization_workflow_returns_404(
        self,
    ):

        self._attach_organization()

        other_workflow = (
            WorkflowDefinition.objects.create(
                organization=(
                    self.other_organization
                ),
                name="Other Workflow",
                code="OTHER_WORKFLOW",
                status=(
                    WorkflowDefinition.STATUS_DRAFT
                ),
            )
        )

        response = self.client.get(
            "/api/workflow/builder/graph/",
            {
                "workflow": str(
                    other_workflow.pk
                )
            },
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_active_workflow_cannot_be_modified(
        self,
    ):

        self._attach_organization()

        self.workflow.status = (
            WorkflowDefinition.STATUS_ACTIVE
        )

        self.workflow.save(
            update_fields=[
                "status",
            ]
        )

        payload = {
            "workflow": str(
                self.workflow.pk
            ),

            "nodes": [
                {
                    "client_id": "start",
                    "name": "Start",
                    "node_type": WorkflowNode.START,
                    "configuration": {},
                },
            ],

            "transitions": [],
        }

        response = self.client.post(
            "/api/workflow/builder/graph/",
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            409,
        )

        self.assertEqual(
            response.data["detail"],
            "Only draft workflows can be edited.",
        )

    def test_draft_graph_can_be_saved(
        self,
    ):

        self._attach_organization()

        payload = {
            "workflow": str(
                self.workflow.pk
            ),

            "nodes": [
                {
                    "client_id": "start-node",
                    "name": "Start",
                    "node_type": WorkflowNode.START,
                    "configuration": {},
                    "position_x": 100,
                    "position_y": 100,
                },
                {
                    "client_id": "end-node",
                    "name": "End",
                    "node_type": WorkflowNode.END,
                    "configuration": {},
                    "position_x": 400,
                    "position_y": 100,
                },
            ],

            "transitions": [
                {
                    "source": "start-node",
                    "target": "end-node",
                    "priority": 100,
                    "condition": "",
                },
            ],
        }

        response = self.client.post(
            "/api/workflow/builder/graph/",
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            WorkflowNode.objects.filter(
                workflow=self.workflow
            ).count(),
            2,
        )

        self.assertEqual(
            WorkflowTransition.objects.filter(
                workflow=self.workflow
            ).count(),
            1,
        )