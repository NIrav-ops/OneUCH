from django.test import TestCase

from inbox.models import Organization

from workflow.models import WorkflowDefinition

from workflow.services.builder.workflow_service import (
    WorkflowBuilderService,
)


class WorkflowVersioningTests(
    TestCase
):

    def setUp(self):

        self.organization = (
            Organization.objects.create(
                name="Versioning Organization"
            )
        )

        self.service = (
            WorkflowBuilderService()
        )

    def create_workflow(
        self,
        *,
        status=WorkflowDefinition.STATUS_DRAFT,
    ):

        return WorkflowDefinition.objects.create(
            organization=self.organization,
            name="Versioned Workflow",
            code="VERSIONED_WORKFLOW",
            description="Version test",
            version=1,
            status=status,
        )

    def test_draft_workflow_can_be_updated(
        self,
    ):

        workflow = self.create_workflow()

        updated = self.service.update_workflow(
            workflow,
            name="Updated Workflow",
            description="Updated description",
        )

        self.assertEqual(
            updated.name,
            "Updated Workflow",
        )

        self.assertEqual(
            updated.description,
            "Updated description",
        )

    def test_active_workflow_cannot_be_updated(
        self,
    ):

        workflow = self.create_workflow(
            status=(
                WorkflowDefinition.STATUS_ACTIVE
            )
        )

        with self.assertRaisesMessage(
            ValueError,
            "Active workflows cannot be modified.",
        ):

            self.service.update_workflow(
                workflow,
                name="Should Not Change",
            )

    def test_archived_workflow_cannot_be_updated(
        self,
    ):

        workflow = self.create_workflow(
            status=(
                WorkflowDefinition.STATUS_ARCHIVED
            )
        )

        with self.assertRaisesMessage(
            ValueError,
            "Archived workflows cannot be modified.",
        ):

            self.service.update_workflow(
                workflow,
                name="Should Not Change",
            )

    def test_active_workflow_cannot_be_deleted(
        self,
    ):

        workflow = self.create_workflow(
            status=(
                WorkflowDefinition.STATUS_ACTIVE
            )
        )

        with self.assertRaisesMessage(
            ValueError,
            "Active workflows cannot be deleted.",
        ):

            self.service.delete_workflow(
                workflow
            )

    def test_archived_workflow_cannot_be_deleted(
        self,
    ):

        workflow = self.create_workflow(
            status=(
                WorkflowDefinition.STATUS_ARCHIVED
            )
        )

        with self.assertRaisesMessage(
            ValueError,
            "Archived workflows cannot be deleted.",
        ):

            self.service.delete_workflow(
                workflow
            )

    def test_draft_workflow_can_be_deleted(
        self,
    ):

        workflow = self.create_workflow()

        workflow_id = workflow.pk

        self.service.delete_workflow(
            workflow
        )

        self.assertFalse(
            WorkflowDefinition.objects.filter(
                pk=workflow_id
            ).exists()
        )