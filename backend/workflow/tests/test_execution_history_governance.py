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
)

from workflow.services.execution import (
    WorkflowExecutionEventService,
)


User = get_user_model()


class WorkflowExecutionHistoryGovernanceTests(
    TestCase
):

    def setUp(self):

        self.organization = (
            Organization.objects.create(
                name="Execution History Governance Organization",
                slug="execution-history-governance-organization",
            )
        )

        self.other_organization = (
            Organization.objects.create(
                name="Other Execution History Organization",
                slug="other-execution-history-organization",
            )
        )

        self.user = User.objects.create_user(
            email="history-governance@example.com",
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
                name="Execution History Governance Workflow",
                code="EXECUTION_HISTORY_GOVERNANCE",
                version=4,
                status=(
                    WorkflowDefinition.STATUS_ACTIVE
                ),
            )
        )

        self.instance = (
            WorkflowInstance.objects.create(
                workflow=self.workflow,
                organization=self.organization,
                started_by=self.user,
                context={},
            )
        )

        WorkflowExecutionEventService.record(
            instance=self.instance,
            event=(
                WorkflowExecutionEventService
                .WORKFLOW_STARTED
            ),
            actor=self.user,
            actor_type="user",
            source="runtime_api",
        )

    def test_authorized_user_can_view_execution_history(
        self,
    ):

        response = self.client.get(
            f"/api/workflow/runtime/"
            f"{self.instance.pk}/history/"
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
            4,
        )

        self.assertEqual(
            len(response.data["events"]),
            1,
        )

    def test_execution_history_preserves_workflow_version(
        self,
    ):

        response = self.client.get(
            f"/api/workflow/runtime/"
            f"{self.instance.pk}/history/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        event = response.data["events"][0]

        self.assertEqual(
            event["details"]["workflow_id"],
            str(self.workflow.pk),
        )

        self.assertEqual(
            event["details"]["workflow_version"],
            4,
        )

    def test_execution_history_contains_actor_context(
        self,
    ):

        response = self.client.get(
            f"/api/workflow/runtime/"
            f"{self.instance.pk}/history/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        event = response.data["events"][0]

        self.assertEqual(
            event["details"]["actor_id"],
            str(self.user.pk),
        )

        self.assertEqual(
            event["details"]["actor_email"],
            self.user.email,
        )

        self.assertEqual(
            event["details"]["actor_type"],
            "user",
        )

        self.assertEqual(
            event["details"]["source"],
            "runtime_api",
        )

    def test_other_organization_instance_is_not_visible(
        self,
    ):

        other_workflow = (
            WorkflowDefinition.objects.create(
                organization=self.other_organization,
                name="Other Organization Workflow",
                code="OTHER_ORGANIZATION_WORKFLOW",
                version=1,
                status=(
                    WorkflowDefinition.STATUS_ACTIVE
                ),
            )
        )

        other_instance = (
            WorkflowInstance.objects.create(
                workflow=other_workflow,
                organization=self.other_organization,
                context={},
            )
        )

        response = self.client.get(
            f"/api/workflow/runtime/"
            f"{other_instance.pk}/history/"
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertFalse(
            WorkflowExecutionLog.objects.filter(
                instance=other_instance
            ).exists()
        )