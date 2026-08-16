from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework.test import APIClient

from inbox.models import (
    Organization,
    OrganizationUser,
)

from workflow.models import (
    WorkflowDefinition,
    WorkflowExecutionLog,
    WorkflowInstance,
    WorkflowNode,
)

User = get_user_model()


class WorkflowExecutionHistoryAPITests(
    TestCase
):

    def setUp(self):

        self.organization = (
            Organization.objects.create(
                name="Execution History Organization",
                slug="execution-history-organization",
            )
        )

        self.other_organization = (
            Organization.objects.create(
                name="Other Execution Organization",
                slug="other-execution-organization",
            )
        )

        self.user = User.objects.create_user(
            email="execution-history@example.com",
            password="test-password",
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=self.organization,
            role="member",
        )

        self.client = APIClient()

        self.client.force_authenticate(
            user=self.user
        )

        self.workflow = (
            WorkflowDefinition.objects.create(
                organization=self.organization,
                name="History Workflow",
                code="HISTORY_WORKFLOW",
                version=1,
                status=(
                    WorkflowDefinition.STATUS_ACTIVE
                ),
            )
        )

        self.start = (
            WorkflowNode.objects.create(
                workflow=self.workflow,
                name="Start",
                node_type=WorkflowNode.START,
                configuration={},
            )
        )

        self.end = (
            WorkflowNode.objects.create(
                workflow=self.workflow,
                name="End",
                node_type=WorkflowNode.END,
                configuration={},
            )
        )

        self.instance = (
            WorkflowInstance.objects.create(
                workflow=self.workflow,
                organization=self.organization,
                context={},
            )
        )

    def _url(self):

        return (
            f"/api/workflow/runtime/"
            f"{self.instance.pk}/history/"
        )

    def test_history_returns_events(
        self,
    ):

        first = (
            WorkflowExecutionLog.objects.create(
                instance=self.instance,
                node=self.start,
                event="workflow_started",
                details={
                    "workflow_version": 1,
                },
            )
        )

        second = (
            WorkflowExecutionLog.objects.create(
                instance=self.instance,
                node=self.start,
                event="node_started",
                details={},
            )
        )

        response = self.client.get(
            self._url()
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["instance"],
            str(self.instance.pk),
        )

        self.assertEqual(
            response.data["workflow"],
            str(self.workflow.pk),
        )

        self.assertEqual(
            response.data["workflow_version"],
            1,
        )

        self.assertEqual(
            len(response.data["events"]),
            2,
        )

        self.assertEqual(
            response.data["events"][0]["id"],
            str(first.pk),
        )

        self.assertEqual(
            response.data["events"][0]["event"],
            "workflow_started",
        )

        self.assertEqual(
            response.data["events"][0]["node"],
            str(self.start.pk),
        )

        self.assertEqual(
            response.data["events"][1]["id"],
            str(second.pk),
        )

    def test_workflow_level_event_has_null_node(
        self,
    ):

        WorkflowExecutionLog.objects.create(
            instance=self.instance,
            event="workflow_started",
            details={},
        )

        response = self.client.get(
            self._url()
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertIsNone(
            response.data["events"][0]["node"]
        )

    def test_history_is_isolated_by_organization(
        self,
    ):

        other_instance = (
            WorkflowInstance.objects.create(
                workflow=self.workflow,
                organization=self.other_organization,
                context={},
            )
        )

        WorkflowExecutionLog.objects.create(
            instance=other_instance,
            event="workflow_started",
            details={},
        )

        response = self.client.get(
            f"/api/workflow/runtime/"
            f"{other_instance.pk}/history/"
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_missing_instance_returns_404(
        self,
    ):

        import uuid

        response = self.client.get(
            f"/api/workflow/runtime/"
            f"{uuid.uuid4()}/history/"
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_history_preserves_workflow_version(
        self,
    ):

        WorkflowExecutionLog.objects.create(
            instance=self.instance,
            event="workflow_started",
            details={
                "workflow_version": 1,
                "workflow_id": str(
                    self.workflow.pk
                ),
            },
        )

        response = self.client.get(
            self._url()
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["workflow_version"],
            1,
        )

        self.assertEqual(
            response.data["events"][0]["details"][
                "workflow_version"
            ],
            1,
        )