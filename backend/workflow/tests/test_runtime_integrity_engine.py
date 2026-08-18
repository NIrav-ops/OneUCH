from django.test import TestCase

from inbox.models import Organization

from workflow.models import (
    WorkflowDefinition,
    WorkflowInstance,
    WorkflowNode,
    WorkflowToken,
    WorkflowTransition,
)

from workflow.services.runtime_engine import (
    WorkflowRuntimeEngine,
)


class WorkflowRuntimeIntegrityEngineTests(
    TestCase
):

    def setUp(self):

        self.organization = (
            Organization.objects.create(
                name="Runtime Integrity Engine Organization",
                slug="runtime-integrity-engine-organization",
            )
        )

        self.workflow = (
            WorkflowDefinition.objects.create(
                organization=self.organization,
                name="Integrity Engine Workflow",
                code="INTEGRITY_ENGINE_WORKFLOW",
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
            )
        )

        self.end = (
            WorkflowNode.objects.create(
                workflow=self.workflow,
                name="End",
                node_type=WorkflowNode.END,
            )
        )

        WorkflowTransition.objects.create(
            workflow=self.workflow,
            source=self.start,
            target=self.end,
        )

        self.instance = (
            WorkflowInstance.objects.create(
                workflow=self.workflow,
                organization=self.organization,
                context={},
            )
        )

    def test_valid_runtime_executes_successfully(
        self,
    ):

        engine = WorkflowRuntimeEngine(
            self.instance,
            actor_type="system",
            source="test",
        )

        result = engine.run()

        result.refresh_from_db()

        self.assertEqual(
            result.status,
            WorkflowInstance.STATUS_COMPLETED,
        )

    def test_cross_workflow_token_is_rejected_before_execution(
        self,
    ):

        other_workflow = (
            WorkflowDefinition.objects.create(
                organization=self.organization,
                name="Other Integrity Workflow",
                code="OTHER_INTEGRITY_ENGINE_WORKFLOW",
                version=1,
                status=(
                    WorkflowDefinition.STATUS_ACTIVE
                ),
            )
        )

        other_node = (
            WorkflowNode.objects.create(
                workflow=other_workflow,
                name="Other Start",
                node_type=WorkflowNode.START,
            )
        )

        WorkflowToken.objects.create(
            instance=self.instance,
            node=other_node,
            status=WorkflowToken.STATUS_ACTIVE,
        )

        engine = WorkflowRuntimeEngine(
            self.instance,
            actor_type="system",
            source="test",
        )

        with self.assertRaises(ValueError):
            engine.run()

        self.instance.refresh_from_db()

        self.assertEqual(
            self.instance.status,
            WorkflowInstance.STATUS_FAILED,
        )

    def test_corrupted_instance_organization_is_rejected(
        self,
    ):

        other_organization = (
            Organization.objects.create(
                name="Other Integrity Organization",
                slug="other-integrity-organization",
            )
        )

        self.instance.organization = (
            other_organization
        )

        self.instance.save(
            update_fields=[
                "organization",
            ]
        )

        engine = WorkflowRuntimeEngine(
            self.instance,
            actor_type="system",
            source="test",
        )

        with self.assertRaises(ValueError):
            engine.run()

        self.instance.refresh_from_db()

        self.assertEqual(
            self.instance.status,
            WorkflowInstance.STATUS_FAILED,
        )

    def test_valid_existing_execution_is_still_rejected_as_already_started(
        self,
    ):

        WorkflowToken.objects.create(
            instance=self.instance,
            node=self.start,
            status=WorkflowToken.STATUS_ACTIVE,
        )

        engine = WorkflowRuntimeEngine(
            self.instance,
            actor_type="system",
            source="test",
        )

        with self.assertRaisesMessage(
            ValueError,
            "Workflow execution has already started.",
        ):
            engine.run()

        self.instance.refresh_from_db()

        self.assertEqual(
            self.instance.status,
            WorkflowInstance.STATUS_RUNNING,
        )

    def test_corrupted_token_does_not_execute(
        self,
    ):

        other_workflow = (
            WorkflowDefinition.objects.create(
                organization=self.organization,
                name="Foreign Workflow",
                code="FOREIGN_RUNTIME_WORKFLOW",
                version=1,
                status=(
                    WorkflowDefinition.STATUS_ACTIVE
                ),
            )
        )

        foreign_node = (
            WorkflowNode.objects.create(
                workflow=other_workflow,
                name="Foreign Node",
                node_type=WorkflowNode.ACTION,
            )
        )

        token = (
            WorkflowToken.objects.create(
                instance=self.instance,
                node=foreign_node,
                status=WorkflowToken.STATUS_ACTIVE,
            )
        )

        engine = WorkflowRuntimeEngine(
            self.instance,
            actor_type="system",
            source="test",
        )

        with self.assertRaises(ValueError):
            engine.execute_node(
                token
            )

        self.instance.refresh_from_db()

        #
        # execute_node itself must reject the token
        # before reaching an executor.
        #
        self.assertEqual(
            self.instance.status,
            WorkflowInstance.STATUS_RUNNING,
        )