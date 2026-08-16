from django.test import TestCase

from inbox.models import Organization

from workflow.models import (
    WorkflowDefinition,
    WorkflowNode,
)

from workflow.services.builder.workflow_service import (
    WorkflowBuilderService,
)


class WorkflowVersionPublishTests(
    TestCase
):

    def setUp(self):

        self.organization = (
            Organization.objects.create(
                name="Version Publish Organization",
                slug="version-publish-organization",
            )
        )

        self.service = (
            WorkflowBuilderService()
        )

        #
        # Version 1
        #

        self.active_v1 = (
            WorkflowDefinition.objects.create(
                organization=self.organization,
                name="Approval Workflow",
                code="APPROVAL_WORKFLOW",
                description="Version one",
                version=1,
                status=(
                    WorkflowDefinition.STATUS_ACTIVE
                ),
            )
        )

        #
        # Version 2
        #

        self.draft_v2 = (
            WorkflowDefinition.objects.create(
                organization=self.organization,
                name="Approval Workflow",
                code="APPROVAL_WORKFLOW",
                description="Version two",
                version=2,
                status=(
                    WorkflowDefinition.STATUS_DRAFT
                ),
            )
        )

        #
        # Validator requires exactly one START node.
        #
        # Create one START node for each workflow version.
        #

        self.active_v1_start = (
            WorkflowNode.objects.create(
                workflow=self.active_v1,
                name="Start",
                node_type=WorkflowNode.START,
                configuration={},
            )
        )

        self.active_v1_end = WorkflowNode.objects.create(
            workflow=self.active_v1,
            name="End",
            node_type=WorkflowNode.END,
            configuration={},
        )

        self.draft_v2_start = (
            WorkflowNode.objects.create(
                workflow=self.draft_v2,
                name="Start",
                node_type=WorkflowNode.START,
                configuration={},
            )
        )

        self.draft_v2_end = WorkflowNode.objects.create(
            workflow=self.draft_v2,
            name="End",
            node_type=WorkflowNode.END,
            configuration={},
        )

    def test_publishing_draft_activates_it(
        self,
    ):

        published = (
            self.service.publish(
                self.draft_v2
            )
        )

        self.assertEqual(
            published.status,
            WorkflowDefinition.STATUS_ACTIVE,
        )

    def test_previous_active_version_is_archived(
        self,
    ):

        self.service.publish(
            self.draft_v2
        )

        self.active_v1.refresh_from_db()

        self.assertEqual(
            self.active_v1.status,
            WorkflowDefinition.STATUS_ARCHIVED,
        )

    def test_only_one_active_version_exists(
        self,
    ):

        self.service.publish(
            self.draft_v2
        )

        active_versions = (
            WorkflowDefinition.objects.filter(
                organization=self.organization,
                code="APPROVAL_WORKFLOW",
                status=(
                    WorkflowDefinition.STATUS_ACTIVE
                ),
            )
        )

        self.assertEqual(
            active_versions.count(),
            1,
        )

        self.assertEqual(
            active_versions.first().pk,
            self.draft_v2.pk,
        )

    def test_active_workflow_cannot_be_published_again(
        self,
    ):

        with self.assertRaisesMessage(
            ValueError,
            "Workflow is already active.",
        ):

            self.service.publish(
                self.active_v1
            )

    def test_non_draft_workflow_cannot_be_published(
        self,
    ):

        archived = (
            WorkflowDefinition.objects.create(
                organization=self.organization,
                name="Approval Workflow",
                code="APPROVAL_WORKFLOW",
                description="Archived version",
                version=3,
                status=(
                    WorkflowDefinition.STATUS_ARCHIVED
                ),
            )
        )

        with self.assertRaisesMessage(
            ValueError,
            "Only draft workflows can be published.",
        ):

            self.service.publish(
                archived
            )

    def test_different_workflow_code_is_not_archived(
        self,
    ):

        other_active = (
            WorkflowDefinition.objects.create(
                organization=self.organization,
                name="Invoice Workflow",
                code="INVOICE_WORKFLOW",
                description="Different workflow",
                version=1,
                status=(
                    WorkflowDefinition.STATUS_ACTIVE
                ),
            )
        )

        #
        # This workflow is intentionally valid because
        # the publish operation validates the draft workflow,
        # not the unrelated active workflow.
        #

        self.service.publish(
            self.draft_v2
        )

        other_active.refresh_from_db()

        self.assertEqual(
            other_active.status,
            WorkflowDefinition.STATUS_ACTIVE,
        )

    def test_different_organization_is_not_archived(
        self,
    ):

        other_organization = (
            Organization.objects.create(
                name="Other Version Organization",
                slug="other-version-organization",
            )
        )

        other_active = (
            WorkflowDefinition.objects.create(
                organization=other_organization,
                name="Approval Workflow",
                code="APPROVAL_WORKFLOW",
                description="Other organization version",
                version=1,
                status=(
                    WorkflowDefinition.STATUS_ACTIVE
                ),
            )
        )

        self.service.publish(
            self.draft_v2
        )

        other_active.refresh_from_db()

        self.assertEqual(
            other_active.status,
            WorkflowDefinition.STATUS_ACTIVE,
        )