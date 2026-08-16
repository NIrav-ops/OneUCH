from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework.test import APIClient

from inbox.models import Organization

from workflow.models import WorkflowDefinition


User = get_user_model()


class WorkflowPublishAPITests(
    TestCase
):

    def setUp(self):

        self.organization = (
            Organization.objects.create(
                name="API Publish Organization"
            )
        )

        self.user = User.objects.create_user(
            email="api-publisher@example.com",
            password="test-password",
        )

        self.client = APIClient()

        self.client.force_authenticate(
            user=self.user
        )

        self.workflow = (
            WorkflowDefinition.objects.create(

                organization=self.organization,

                name="API Workflow",

                code="API_WORKFLOW",

                status=(
                    WorkflowDefinition.STATUS_DRAFT
                ),

                created_by=self.user,
            )
        )

    def test_missing_workflow_returns_404(
        self,
    ):

        import uuid

        response = self.client.post(
            (
                "/api/workflow/definitions/"
                f"{uuid.uuid4()}/publish/"
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )