from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from inbox.models import Organization

from workflow.models import (
    WorkflowDefinition,
)

from workflow.services.builder.workflow_service import (
    WorkflowBuilderService,
)


User = get_user_model()


class WorkflowPublishServiceTests(
    TestCase
):

    def setUp(self):

        self.organization = (
            Organization.objects.create(
                name="Publish Test Organization"
            )
        )

        self.user = User.objects.create_user(
            email="workflow-publisher@example.com",
            password="test-password",
        )

        self.workflow = (
            WorkflowDefinition.objects.create(

                organization=self.organization,

                name="Test Workflow",

                code="TEST_WORKFLOW",

                description="Test workflow",

                created_by=self.user,

                status=(
                    WorkflowDefinition.STATUS_DRAFT
                ),
            )
        )

        self.service = (
            WorkflowBuilderService()
        )

    @patch(
        "workflow.services.builder.workflow_service.WorkflowValidator.validate"
    )
    def test_publish_draft_workflow(
        self,
        mock_validate,
    ):

        result = self.service.publish(
            self.workflow
        )

        self.assertEqual(
            result.status,
            WorkflowDefinition.STATUS_ACTIVE,
        )

        mock_validate.assert_called_once_with(
            self.workflow
        )

        self.workflow.refresh_from_db()

        self.assertEqual(
            self.workflow.status,
            WorkflowDefinition.STATUS_ACTIVE,
        )

    def test_publish_active_workflow_fails(
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

        with self.assertRaises(
            ValueError
        ) as context:

            self.service.publish(
                self.workflow
            )

        self.assertEqual(
            str(context.exception),
            "Workflow is already active.",
        )

    def test_publish_non_draft_workflow_fails(
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

        with self.assertRaises(
            ValueError
        ) as context:

            self.service.publish(
                self.workflow
            )

        self.assertEqual(
            str(context.exception),
            "Only draft workflows can be published.",
        )

    @patch(
        "workflow.services.builder.workflow_service.WorkflowValidator.validate"
    )
    def test_publish_validation_failure(
        self,
        mock_validate,
    ):

        mock_validate.side_effect = ValueError(
            "Workflow must contain an end node."
        )

        with self.assertRaises(
            ValueError
        ) as context:

            self.service.publish(
                self.workflow
            )

        self.assertEqual(
            str(context.exception),
            "Workflow must contain an end node.",
        )

        self.workflow.refresh_from_db()

        self.assertEqual(
            self.workflow.status,
            WorkflowDefinition.STATUS_DRAFT,
        )