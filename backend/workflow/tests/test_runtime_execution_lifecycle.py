from django.contrib.auth import get_user_model
from django.test import TestCase

from inbox.models import (
    Organization,
    OrganizationUser,
)

from workflow.models import (
    WorkflowDefinition,
    WorkflowNode,
    WorkflowInstance,
    WorkflowToken,
)

from workflow.services.runtime_engine import (
    WorkflowRuntimeEngine,
)


User = get_user_model()


class WorkflowRuntimeExecutionLifecycleTests(
    TestCase
):

    def setUp(self):

        self.organization = Organization.objects.create(
            name="Runtime Lifecycle Organization",
            slug="runtime-lifecycle-organization",
        )

        self.user = User.objects.create_user(
            email="runtime-lifecycle@example.com",
            password="test-password",
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=self.organization,
            role="member",
        )

        self.workflow = WorkflowDefinition.objects.create(
            organization=self.organization,
            name="Lifecycle Workflow",
            code="LIFECYCLE_WORKFLOW",
            version=1,
            status=WorkflowDefinition.STATUS_ACTIVE,
        )

        self.start = WorkflowNode.objects.create(
            workflow=self.workflow,
            name="Start",
            node_type=WorkflowNode.START,
        )

        self.end = WorkflowNode.objects.create(
            workflow=self.workflow,
            name="End",
            node_type=WorkflowNode.END,
        )

        self.instance = WorkflowInstance.objects.create(
            workflow=self.workflow,
            organization=self.organization,
            started_by=self.user,
            context={},
        )

    def test_run_requires_valid_start_node(self):

        WorkflowNode.objects.filter(
            pk=self.start.pk
        ).delete()

        engine = WorkflowRuntimeEngine(
            self.instance,
            actor=self.user,
            actor_type="user",
            source="test",
        )

        with self.assertRaisesMessage(
            ValueError,
            "Workflow has no START node.",
        ):
            engine.run()

        self.instance.refresh_from_db()

        self.assertEqual(
            self.instance.status,
            WorkflowInstance.STATUS_FAILED,
        )

    def test_multiple_start_nodes_are_rejected(self):

        WorkflowNode.objects.create(
            workflow=self.workflow,
            name="Second Start",
            node_type=WorkflowNode.START,
        )

        engine = WorkflowRuntimeEngine(
            self.instance,
            actor=self.user,
            actor_type="user",
            source="test",
        )

        with self.assertRaisesMessage(
            ValueError,
            "Workflow has multiple START nodes.",
        ):
            engine.run()

        self.instance.refresh_from_db()

        self.assertEqual(
            self.instance.status,
            WorkflowInstance.STATUS_FAILED,
        )

    def test_runtime_cannot_be_started_twice(self):

        engine = WorkflowRuntimeEngine(
            self.instance,
            actor=self.user,
            actor_type="user",
            source="test",
        )

        #
        # START has no outgoing transition in this test,
        # so the first run will fail rather than create a
        # second execution.
        #

        with self.assertRaises(ValueError):
            engine.run()

        token_count = WorkflowToken.objects.filter(
            instance=self.instance
        ).count()

        self.assertEqual(
            token_count,
            1,
        )

        self.instance.refresh_from_db()

        self.assertEqual(
            self.instance.status,
            WorkflowInstance.STATUS_FAILED,
        )

    def test_non_end_node_without_transition_fails(self):

        engine = WorkflowRuntimeEngine(
            self.instance,
            actor=self.user,
            actor_type="user",
            source="test",
        )

        with self.assertRaisesMessage(
            ValueError,
            "has no valid outgoing transition",
        ):
            engine.run()

        self.instance.refresh_from_db()

        self.assertEqual(
            self.instance.status,
            WorkflowInstance.STATUS_FAILED,
        )

    def test_end_node_is_valid_terminal_condition(self):

        from workflow.models import WorkflowTransition

        WorkflowTransition.objects.create(
            workflow=self.workflow,
            source=self.start,
            target=self.end,
        )

        engine = WorkflowRuntimeEngine(
            self.instance,
            actor=self.user,
            actor_type="user",
            source="test",
        )

        result = engine.run()

        result.refresh_from_db()

        self.assertEqual(
            result.status,
            WorkflowInstance.STATUS_COMPLETED,
        )

    def test_running_runtime_cannot_be_started_twice(self):

        WorkflowToken.objects.create(
            instance=self.instance,
            node=self.start,
            status=WorkflowToken.STATUS_ACTIVE,
        )

        engine = WorkflowRuntimeEngine(
            self.instance,
            actor=self.user,
            actor_type="user",
            source="test",
        )

        with self.assertRaisesMessage(
            ValueError,
            "Workflow execution has already started.",
        ):
            engine.run()