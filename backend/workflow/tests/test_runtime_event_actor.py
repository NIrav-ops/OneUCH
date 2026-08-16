from django.contrib.auth import get_user_model

from django.test import TestCase

from inbox.models import (
    Organization,
    OrganizationUser,
)

from workflow.models import (
    WorkflowDefinition,
    WorkflowExecutionLog,
    WorkflowInstance,
)

from workflow.services.runtime_engine import (
    WorkflowRuntimeEngine,
)

from workflow.services.execution import (
    WorkflowExecutionEventService,
)


User = get_user_model()


class WorkflowRuntimeEventActorTests(
    TestCase
):

    def setUp(self):

        self.organization = (
            Organization.objects.create(
                name="Runtime Actor Organization",
                slug="runtime-actor-organization",
            )
        )

        self.user = User.objects.create_user(
            email="runtime-actor@example.com",
            password="test-password",
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=self.organization,
            role="member",
        )

        self.workflow = (
            WorkflowDefinition.objects.create(
                organization=self.organization,
                name="Runtime Actor Workflow",
                code="RUNTIME_ACTOR_WORKFLOW",
                version=1,
            )
        )

        self.instance = (
            WorkflowInstance.objects.create(
                workflow=self.workflow,
                organization=self.organization,
                started_by=None,
                context={},
            )
        )

    def test_runtime_engine_propagates_actor_context(self):

        engine = WorkflowRuntimeEngine(
            self.instance,
            actor=self.user,
            actor_type="user",
            source="runtime_api",
        )

        engine._record_event(
            event=(
                WorkflowExecutionEventService
                .WORKFLOW_STARTED
            ),
        )

        event = (
            WorkflowExecutionLog.objects
            .order_by("-created_at")
            .first()
        )

        self.assertEqual(
            event.details["actor_id"],
            str(self.user.pk),
        )

        self.assertEqual(
            event.details["actor_email"],
            self.user.email,
        )

        self.assertEqual(
            event.details["actor_type"],
            "user",
        )

        self.assertEqual(
            event.details["source"],
            "runtime_api",
        )

        self.assertEqual(
            event.details["workflow_id"],
            str(self.workflow.pk),
        )

        self.assertEqual(
            event.details["workflow_version"],
            self.workflow.version,
        )