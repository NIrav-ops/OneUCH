from django.test import TestCase

from inbox.models import Organization

from workflow.models import (
    WorkflowDefinition,
    WorkflowNode,
    WorkflowTransition,
)

from workflow.services.builder.workflow_service import (
    WorkflowBuilderService,
)


class WorkflowVersionCreationTests(
    TestCase
):

    def setUp(self):

        self.organization = (
            Organization.objects.create(
                name="Version Creation Organization"
            )
        )

        self.service = (
            WorkflowBuilderService()
        )

        self.workflow = (
            WorkflowDefinition.objects.create(
                organization=self.organization,
                name="Approval Workflow",
                code="APPROVAL_WORKFLOW",
                description="Original workflow",
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
                configuration={
                    "source": "email"
                },
                position_x=100,
                position_y=200,
            )
        )

        self.end = (
            WorkflowNode.objects.create(
                workflow=self.workflow,
                name="End",
                node_type=WorkflowNode.END,
                configuration={
                    "result": "complete"
                },
                position_x=400,
                position_y=200,
            )
        )

        self.transition = (
            WorkflowTransition.objects.create(
                workflow=self.workflow,
                source=self.start,
                target=self.end,
                condition="",
                priority=100,
            )
        )

    def test_new_version_is_created_as_draft(
        self,
    ):

        new_workflow = (
            self.service.create_new_version(
                self.workflow
            )
        )

        self.assertNotEqual(
            new_workflow.pk,
            self.workflow.pk,
        )

        self.assertEqual(
            new_workflow.version,
            2,
        )

        self.assertEqual(
            new_workflow.status,
            WorkflowDefinition.STATUS_DRAFT,
        )

        self.assertEqual(
            new_workflow.code,
            self.workflow.code,
        )

    def test_original_version_remains_active(
        self,
    ):

        new_workflow = (
            self.service.create_new_version(
                self.workflow
            )
        )

        self.workflow.refresh_from_db()

        self.assertEqual(
            self.workflow.version,
            1,
        )

        self.assertEqual(
            self.workflow.status,
            WorkflowDefinition.STATUS_ACTIVE,
        )

        self.assertEqual(
            new_workflow.version,
            2,
        )

    def test_nodes_are_copied(
        self,
    ):

        new_workflow = (
            self.service.create_new_version(
                self.workflow
            )
        )

        nodes = (
            WorkflowNode.objects.filter(
                workflow=new_workflow
            ).order_by("name")
        )

        self.assertEqual(
            nodes.count(),
            2,
        )

        names = set(
            nodes.values_list(
                "name",
                flat=True,
            )
        )

        self.assertEqual(
            names,
            {
                "Start",
                "End",
            },
        )

    def test_node_configuration_and_position_are_copied(
        self,
    ):

        new_workflow = (
            self.service.create_new_version(
                self.workflow
            )
        )

        new_start = (
            WorkflowNode.objects.get(
                workflow=new_workflow,
                name="Start",
            )
        )

        self.assertEqual(
            new_start.configuration,
            {
                "source": "email"
            },
        )

        self.assertEqual(
            new_start.position_x,
            100,
        )

        self.assertEqual(
            new_start.position_y,
            200,
        )

    def test_transitions_are_copied(
        self,
    ):

        new_workflow = (
            self.service.create_new_version(
                self.workflow
            )
        )

        transitions = (
            WorkflowTransition.objects.filter(
                workflow=new_workflow
            )
        )

        self.assertEqual(
            transitions.count(),
            1,
        )

        transition = transitions.first()

        self.assertEqual(
            transition.source,
            WorkflowNode.objects.get(
                workflow=new_workflow,
                name="Start",
            ),
        )

        self.assertEqual(
            transition.target,
            WorkflowNode.objects.get(
                workflow=new_workflow,
                name="End",
            ),
        )

    def test_new_version_has_independent_nodes(
        self,
    ):

        new_workflow = (
            self.service.create_new_version(
                self.workflow
            )
        )

        new_start = (
            WorkflowNode.objects.get(
                workflow=new_workflow,
                name="Start",
            )
        )

        new_start.name = "Modified Start"
        new_start.save()

        self.start.refresh_from_db()

        self.assertEqual(
            self.start.name,
            "Start",
        )

        self.assertEqual(
            new_start.name,
            "Modified Start",
        )

    def test_non_active_workflow_cannot_create_version(
        self,
    ):

        draft = (
            WorkflowDefinition.objects.create(
                organization=self.organization,
                name="Draft Workflow",
                code="DRAFT_WORKFLOW",
                version=1,
                status=(
                    WorkflowDefinition.STATUS_DRAFT
                ),
            )
        )

        with self.assertRaisesMessage(
            ValueError,
            "Only active workflows can create a new version.",
        ):

            self.service.create_new_version(
                draft
            )