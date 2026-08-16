from django.test import TestCase

from inbox.models import Organization

from workflow.models import (
    WorkflowDefinition,
    WorkflowInstance,
    WorkflowNode,
)

from workflow.services.context import (
    WorkflowExecutionContext,
)

from workflow.services.execution.events import (
    WorkflowExecutionEventService,
)


class WorkflowRuntimeVersionPinningTests(
    TestCase
):

    def setUp(self):

        self.organization = (
            Organization.objects.create(
                name="Runtime Version Organization",
                slug="runtime-version-organization",
            )
        )

        self.workflow_v1 = (
            WorkflowDefinition.objects.create(
                organization=self.organization,
                name="Approval Workflow",
                code="APPROVAL_WORKFLOW",
                version=1,
                status=(
                    WorkflowDefinition.STATUS_ARCHIVED
                ),
            )
        )

        self.workflow_v2 = (
            WorkflowDefinition.objects.create(
                organization=self.organization,
                name="Approval Workflow",
                code="APPROVAL_WORKFLOW",
                version=2,
                status=(
                    WorkflowDefinition.STATUS_ACTIVE
                ),
            )
        )

        WorkflowNode.objects.create(
            workflow=self.workflow_v1,
            name="Start",
            node_type=WorkflowNode.START,
            configuration={},
        )

        WorkflowNode.objects.create(
            workflow=self.workflow_v1,
            name="End",
            node_type=WorkflowNode.END,
            configuration={},
        )

        WorkflowNode.objects.create(
            workflow=self.workflow_v2,
            name="Start",
            node_type=WorkflowNode.START,
            configuration={},
        )

        WorkflowNode.objects.create(
            workflow=self.workflow_v2,
            name="End",
            node_type=WorkflowNode.END,
            configuration={},
        )

    def test_instance_is_pinned_to_exact_workflow_definition(
        self,
    ):

        instance = (
            WorkflowInstance.objects.create(
                workflow=self.workflow_v1,
                organization=self.organization,
                context={},
            )
        )

        self.assertEqual(
            instance.workflow_id,
            self.workflow_v1.pk,
        )

        self.assertEqual(
            instance.workflow.version,
            1,
        )

        self.workflow_v1.status = (
            WorkflowDefinition.STATUS_ARCHIVED
        )

        self.workflow_v1.save(
            update_fields=[
                "status",
            ]
        )

        instance.refresh_from_db()

        self.assertEqual(
            instance.workflow_id,
            self.workflow_v1.pk,
        )

        self.assertEqual(
            instance.workflow.version,
            1,
        )

    def test_context_exposes_pinned_workflow_version(
        self,
    ):

        instance = (
            WorkflowInstance.objects.create(
                workflow=self.workflow_v1,
                organization=self.organization,
                context={},
            )
        )

        context = (
            WorkflowExecutionContext(
                instance
            )
        )

        self.assertEqual(
            context.workflow_id,
            str(
                self.workflow_v1.pk
            ),
        )

        self.assertEqual(
            context.workflow_code,
            "APPROVAL_WORKFLOW",
        )

        self.assertEqual(
            context.workflow_version,
            1,
        )

    def test_new_instance_uses_new_active_version(
        self,
    ):

        instance = (
            WorkflowInstance.objects.create(
                workflow=self.workflow_v2,
                organization=self.organization,
                context={},
            )
        )

        self.assertEqual(
            instance.workflow_id,
            self.workflow_v2.pk,
        )

        self.assertEqual(
            instance.workflow.version,
            2,
        )

    def test_runtime_event_contains_workflow_version(
        self,
    ):

        instance = (
            WorkflowInstance.objects.create(
                workflow=self.workflow_v1,
                organization=self.organization,
                context={},
            )
        )

        event = (
            WorkflowExecutionEventService.record(
                instance=instance,
                event=(
                    WorkflowExecutionEventService.NODE_STARTED
                ),
            )
        )

        self.assertEqual(
            event.instance_id,
            instance.pk,
        )

        self.assertEqual(
            event.event,
            WorkflowExecutionEventService.NODE_STARTED,
        )

        self.assertEqual(
            event.details["workflow_version"],
            self.workflow_v1.version,
        )

        self.assertEqual(
            event.details["workflow_version"],
            1,
        )

        self.assertEqual(
            event.details["workflow_id"],
            str(
                self.workflow_v1.pk
            ),
        )