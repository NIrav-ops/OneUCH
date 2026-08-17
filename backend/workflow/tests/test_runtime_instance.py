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


class WorkflowRuntimeInstanceTests(
    TestCase
):

    def setUp(self):

        self.organization = (
            Organization.objects.create(
                name="Runtime Instance Organization",
                slug="runtime-instance-organization",
            )
        )

        self.other_organization = (
            Organization.objects.create(
                name="Other Runtime Instance Organization",
                slug="other-runtime-instance-organization",
            )
        )

        self.user = User.objects.create_user(
            email="runtime-instance@example.com",
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
                name="Runtime Instance Workflow",
                code="RUNTIME_INSTANCE_WORKFLOW",
                version=3,
                status=(
                    WorkflowDefinition.STATUS_ACTIVE
                ),
            )
        )

    def test_create_runtime_instance(
        self,
    ):

        response = self.client.post(
            f"/api/workflow/definitions/"
            f"{self.workflow.pk}/runtime/",
            {
                "context": {
                    "customer_id": "CUST-001",
                    "priority": "high",
                },
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        instance = (
            WorkflowInstance.objects.get(
                pk=response.data["id"]
            )
        )

        self.assertEqual(
            instance.workflow_id,
            self.workflow.pk,
        )

        self.assertEqual(
            instance.organization_id,
            self.organization.pk,
        )

        self.assertEqual(
            instance.started_by_id,
            self.user.pk,
        )

        self.assertEqual(
            instance.status,
            WorkflowInstance.STATUS_RUNNING,
        )

        self.assertEqual(
            instance.context,
            {
                "customer_id": "CUST-001",
                "priority": "high",
            },
        )

        self.assertEqual(
            response.data["workflow"],
            str(self.workflow.pk),
        )

    def test_runtime_instance_is_pinned_to_exact_workflow_version(
        self,
    ):

        response = self.client.post(
            f"/api/workflow/definitions/"
            f"{self.workflow.pk}/runtime/",
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        instance = (
            WorkflowInstance.objects.get(
                pk=response.data["id"]
            )
        )

        self.assertEqual(
            instance.workflow.version,
            3,
        )

        self.assertEqual(
            instance.workflow.pk,
            self.workflow.pk,
        )

    def test_other_organization_workflow_returns_404(
        self,
    ):

        other_workflow = (
            WorkflowDefinition.objects.create(
                organization=self.other_organization,
                name="Other Organization Workflow",
                code="OTHER_ORG_WORKFLOW",
                version=1,
                status=(
                    WorkflowDefinition.STATUS_ACTIVE
                ),
            )
        )

        response = self.client.post(
            f"/api/workflow/definitions/"
            f"{other_workflow.pk}/runtime/",
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertFalse(
            WorkflowInstance.objects.filter(
                workflow=other_workflow
            ).exists()
        )

    def test_draft_workflow_cannot_be_executed(
        self,
    ):

        self.workflow.status = (
            WorkflowDefinition.STATUS_DRAFT
        )

        self.workflow.save(
            update_fields=[
                "status",
            ]
        )

        response = self.client.post(
            f"/api/workflow/definitions/"
            f"{self.workflow.pk}/runtime/",
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            409,
        )

        self.assertFalse(
            WorkflowInstance.objects.filter(
                workflow=self.workflow
            ).exists()
        )

    def test_disabled_workflow_cannot_be_executed(
        self,
    ):

        self.workflow.status = (
            WorkflowDefinition.STATUS_DISABLED
        )

        self.workflow.save(
            update_fields=[
                "status",
            ]
        )

        response = self.client.post(
            f"/api/workflow/definitions/"
            f"{self.workflow.pk}/runtime/",
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            409,
        )

    def test_invalid_context_returns_400(
        self,
    ):

        response = self.client.post(
            f"/api/workflow/definitions/"
            f"{self.workflow.pk}/runtime/",
            {
                "context": [
                    "invalid",
                    "context",
                ],
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertEqual(
            WorkflowInstance.objects.count(),
            0,
        )

    def test_default_context_is_empty_dictionary(
        self,
    ):

        response = self.client.post(
            f"/api/workflow/definitions/"
            f"{self.workflow.pk}/runtime/",
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        instance = (
            WorkflowInstance.objects.get(
                pk=response.data["id"]
            )
        )

        self.assertEqual(
            instance.context,
            {},
        )

    def test_created_instance_has_running_status(
        self,
    ):

        response = self.client.post(
            f"/api/workflow/definitions/"
            f"{self.workflow.pk}/runtime/",
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertEqual(
            response.data["status"],
            WorkflowInstance.STATUS_RUNNING,
        )