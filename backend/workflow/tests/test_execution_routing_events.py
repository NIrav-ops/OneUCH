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
    WorkflowNode,
    WorkflowTransition,
)

from workflow.services.runtime_engine import (
    WorkflowRuntimeEngine,
)


User = get_user_model()


class WorkflowExecutionRoutingEventTests(
    TestCase
):

    def setUp(self):

        self.organization = (
            Organization.objects.create(
                name="Routing Events Organization",
                slug="routing-events-organization",
            )
        )

        self.user = User.objects.create_user(
            email="routing-events@example.com",
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
                name="Routing Events Workflow",
                code="ROUTING_EVENTS_WORKFLOW",
                version=1,
                status=(
                    WorkflowDefinition.STATUS_ACTIVE
                ),
            )
        )

        self.instance = (
            WorkflowInstance.objects.create(
                workflow=self.workflow,
                organization=self.organization,
                started_by=self.user,
                context={
                    "priority": "high",
                },
            )
        )

        self.start = (
            WorkflowNode.objects.create(
                workflow=self.workflow,
                name="Start",
                node_type=WorkflowNode.START,
            )
        )

        self.high_priority = (
            WorkflowNode.objects.create(
                workflow=self.workflow,
                name="High Priority",
                node_type=WorkflowNode.END,
            )
        )

        self.default_node = (
            WorkflowNode.objects.create(
                workflow=self.workflow,
                name="Default",
                node_type=WorkflowNode.END,
            )
        )

        self.engine = WorkflowRuntimeEngine(
            self.instance,
            actor=self.user,
            actor_type="user",
            source="runtime_test",
        )

    def test_matching_condition_records_transition_selected(self):

        transition = (
            WorkflowTransition.objects.create(
                workflow=self.workflow,
                source=self.start,
                target=self.high_priority,
                condition="priority == 'high'",
                priority=1,
            )
        )

        result = self.engine.get_next_node(
            self.start,
            self.engine.context,
        )

        self.assertEqual(
            result,
            self.high_priority,
        )

        event = (
            WorkflowExecutionLog.objects
            .filter(
                instance=self.instance,
                event="transition_selected",
            )
            .latest("created_at")
        )

        self.assertEqual(
            event.details["transition_id"],
            str(transition.pk),
        )

        self.assertEqual(
            event.details["source_node_id"],
            str(self.start.pk),
        )

        self.assertEqual(
            event.details["target_node_id"],
            str(self.high_priority.pk),
        )

        self.assertEqual(
            event.details["evaluation"],
            "condition_matched",
        )

    def test_default_transition_records_transition_selected(self):

        transition = (
            WorkflowTransition.objects.create(
                workflow=self.workflow,
                source=self.start,
                target=self.default_node,
                condition="",
                priority=10,
            )
        )

        result = self.engine.get_next_node(
            self.start,
            self.engine.context,
        )

        self.assertEqual(
            result,
            self.default_node,
        )

        event = (
            WorkflowExecutionLog.objects
            .filter(
                instance=self.instance,
                event="transition_selected",
            )
            .latest("created_at")
        )

        self.assertEqual(
            event.details["transition_id"],
            str(transition.pk),
        )

        self.assertEqual(
            event.details["evaluation"],
            "default_transition",
        )

    def test_no_matching_transition_records_rejection(self):

        WorkflowTransition.objects.create(
            workflow=self.workflow,
            source=self.start,
            target=self.high_priority,
            condition="priority == 'low'",
            priority=1,
        )

        result = self.engine.get_next_node(
            self.start,
            self.engine.context,
        )

        self.assertIsNone(
            result
        )

        event = (
            WorkflowExecutionLog.objects
            .filter(
                instance=self.instance,
                event="transition_rejected",
            )
            .latest("created_at")
        )

        self.assertEqual(
            event.details["source_node_id"],
            str(self.start.pk),
        )

        self.assertEqual(
            event.details["evaluation"],
            "no_transition_available",
        )

    def test_node_without_transitions_records_rejection(self):

        result = self.engine.get_next_node(
            self.start,
            self.engine.context,
        )

        self.assertIsNone(
            result
        )

        event = (
            WorkflowExecutionLog.objects
            .filter(
                instance=self.instance,
                event="transition_rejected",
            )
            .latest("created_at")
        )

        self.assertEqual(
            event.details["source_node_id"],
            str(self.start.pk),
        )

        self.assertEqual(
            event.details["evaluation"],
            "no_outgoing_transition",
        )

    def test_routing_event_does_not_store_runtime_variables(self):

        WorkflowTransition.objects.create(
            workflow=self.workflow,
            source=self.start,
            target=self.high_priority,
            condition="priority == 'high'",
            priority=1,
        )

        self.engine.get_next_node(
            self.start,
            self.engine.context,
        )

        event = (
            WorkflowExecutionLog.objects
            .filter(
                instance=self.instance,
                event="transition_selected",
            )
            .latest("created_at")
        )

        self.assertNotIn(
            "variables",
            event.details,
        )

        self.assertNotIn(
            "priority",
            event.details,
        )