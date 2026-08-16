from django.contrib.auth import get_user_model

from django.test import TestCase

from rest_framework.test import APIClient

from inbox.models import (
    Organization,
    OrganizationUser,
)

from workflow.models import (
    WorkflowDefinition,
    WorkflowInstance,
)

User = get_user_model()


class WorkflowRuntimeAPITests(
    TestCase
):

    def setUp(self):

        self.organization = (
            Organization.objects.create(
                name="Runtime API Organization",
                slug="runtime-api-organization",
            )
        )

        self.other_organization = (
            Organization.objects.create(
                name="Other Runtime Organization",
                slug="other-runtime-organization",
            )
        )

        self.user = User.objects.create_user(
            email="runtime-api@example.com",
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
                name="Runtime API Workflow",
                code="RUNTIME_API_WORKFLOW",
                version=1,
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

    def test_get_instance(
        self,
    ):

        response = self.client.get(
            f"/api/workflow/runtime/"
            f"{self.instance.pk}/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["id"],
            str(self.instance.pk),
        )

        self.assertEqual(
            response.data["workflow"],
            str(self.workflow.pk),
        )

    def test_other_organization_instance_returns_404(
        self,
    ):

        other_workflow = (
            WorkflowDefinition.objects.create(
                organization=self.other_organization,
                name="Other Runtime Workflow",
                code="OTHER_RUNTIME_WORKFLOW",
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
            f"{other_instance.pk}/"
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_invalid_action_returns_400(
        self,
    ):

        response = self.client.post(
            f"/api/workflow/runtime/"
            f"{self.instance.pk}/",
            {
                "action": "invalid",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

    def test_cancel_action(
        self,
    ):

        response = self.client.post(
            f"/api/workflow/runtime/"
            f"{self.instance.pk}/",
            {
                "action": "cancel",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.instance.refresh_from_db()

        self.assertEqual(
            self.instance.status,
            WorkflowInstance.STATUS_CANCELLED,
        )

    def test_cancelled_instance_cannot_run_again(
        self,
    ):

        self.instance.status = (
            WorkflowInstance.STATUS_CANCELLED
        )

        self.instance.save(
            update_fields=[
                "status",
            ]
        )

        response = self.client.post(
            f"/api/workflow/runtime/"
            f"{self.instance.pk}/",
            {
                "action": "run",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.instance.refresh_from_db()

        self.assertEqual(
            self.instance.status,
            WorkflowInstance.STATUS_CANCELLED,
        )