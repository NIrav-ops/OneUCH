from unittest.mock import patch

from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APITestCase

from inbox.models import (
    Organization,
    OrganizationUser,
)

from workflow.models import (
    WorkflowDefinition,
)


User = get_user_model()


class WorkflowTenantIsolationAPITests(
    APITestCase
):

    def setUp(self):

        # -----------------------------------------------------
        # Tenant A
        # -----------------------------------------------------

        self.organization_a = (
            Organization.objects.create(
                name="Workflow Tenant A",
                slug="workflow-tenant-a",
            )
        )

        self.user_a = (
            User.objects.create_user(
                email="workflow-a@example.com",
                password="Password123",
            )
        )

        OrganizationUser.objects.create(
            user=self.user_a,
            organization=self.organization_a,
            role="member",
        )

        # -----------------------------------------------------
        # Tenant B
        # -----------------------------------------------------

        self.organization_b = (
            Organization.objects.create(
                name="Workflow Tenant B",
                slug="workflow-tenant-b",
            )
        )

        self.user_b = (
            User.objects.create_user(
                email="workflow-b@example.com",
                password="Password123",
            )
        )

        OrganizationUser.objects.create(
            user=self.user_b,
            organization=self.organization_b,
            role="member",
        )

        # -----------------------------------------------------
        # Workflows
        # -----------------------------------------------------

        self.workflow_a = (
            WorkflowDefinition.objects.create(
                organization=self.organization_a,
                name="Tenant A Workflow",
                code="TENANT_A_WORKFLOW",
                status=(
                    WorkflowDefinition.STATUS_DRAFT
                ),
                created_by=self.user_a,
            )
        )

        self.workflow_b = (
            WorkflowDefinition.objects.create(
                organization=self.organization_b,
                name="Tenant B Workflow",
                code="TENANT_B_WORKFLOW",
                status=(
                    WorkflowDefinition.STATUS_DRAFT
                ),
                created_by=self.user_b,
            )
        )

        self.client.force_authenticate(
            user=self.user_a,
        )

    # ========================================================
    # DEFINITION DETAIL
    # ========================================================

    def test_user_can_read_own_workflow_definition(
        self,
    ):

        response = self.client.get(
            (
                "/api/workflow/definitions/"
                f"{self.workflow_a.pk}/"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_cross_tenant_workflow_definition_is_404(
        self,
    ):

        response = self.client.get(
            (
                "/api/workflow/definitions/"
                f"{self.workflow_b.pk}/"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    # ========================================================
    # DEFINITION LIST
    # ========================================================

    def test_workflow_list_contains_only_current_tenant(
        self,
    ):

        response = self.client.get(
            "/api/workflow/definitions/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        returned_ids = {
            str(item["id"])
            for item in response.data
        }

        self.assertIn(
            str(self.workflow_a.pk),
            returned_ids,
        )

        self.assertNotIn(
            str(self.workflow_b.pk),
            returned_ids,
        )

    # ========================================================
    # PUBLISH
    # ========================================================

    @patch(
        "workflow.views_publish."
        "WorkflowBuilderService.publish"
    )
    def test_user_can_reach_publish_for_own_workflow(
        self,
        mock_publish,
    ):

        mock_publish.return_value = (
            self.workflow_a
        )

        response = self.client.post(
            (
                "/api/workflow/definitions/"
                f"{self.workflow_a.pk}/publish/"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        mock_publish.assert_called_once()

        called_workflow = (
            mock_publish.call_args.args[0]
        )

        self.assertEqual(
            called_workflow.pk,
            self.workflow_a.pk,
        )

    @patch(
        "workflow.views_publish."
        "WorkflowBuilderService.publish"
    )
    def test_cross_tenant_publish_returns_404(
        self,
        mock_publish,
    ):

        response = self.client.post(
            (
                "/api/workflow/definitions/"
                f"{self.workflow_b.pk}/publish/"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        mock_publish.assert_not_called()

    # ========================================================
    # NO MEMBERSHIP
    # ========================================================

    def test_user_without_membership_cannot_read_workflow(
        self,
    ):

        outsider = User.objects.create_user(
            email="workflow-outsider@example.com",
            password="Password123",
        )

        self.client.force_authenticate(
            user=outsider,
        )

        response = self.client.get(
            (
                "/api/workflow/definitions/"
                f"{self.workflow_a.pk}/"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_user_without_membership_cannot_publish(
        self,
    ):

        outsider = User.objects.create_user(
            email="workflow-outsider2@example.com",
            password="Password123",
        )

        self.client.force_authenticate(
            user=outsider,
        )

        response = self.client.post(
            (
                "/api/workflow/definitions/"
                f"{self.workflow_a.pk}/publish/"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    # ========================================================
    # AUTHENTICATION
    # ========================================================

    def test_unauthenticated_definition_access_is_401(
        self,
    ):

        self.client.force_authenticate(
            user=None,
        )

        response = self.client.get(
            "/api/workflow/definitions/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
