from django.test import TestCase

from workflow.models import (
    WorkflowNode,
    WorkflowInstance,
    WorkflowToken,
)
from workflow.services.context import WorkflowExecutionContext
from workflow.services.executors.factory import ExecutorFactory
from workflow.tests.utils import create_workflow
from actions.models import ActionItem
from approvals.models import ApprovalItem
from notifications.models import Notification


class EnterpriseExecutorTests(TestCase):

    def _execute(self, node_type):

        workflow = create_workflow()

        node = WorkflowNode.objects.create(
            workflow=workflow,
            name=node_type,
            node_type=node_type,
        )

        instance = WorkflowInstance.objects.create(
            workflow=workflow,
            organization=workflow.organization,
        )

        token = WorkflowToken.objects.create(
            instance=instance,
            node=node,
        )

        context = WorkflowExecutionContext(instance)

        executor = ExecutorFactory.get_executor(
            node_type
        )(context, token)

        executor.execute()

        return context

    def test_action_executor(self):

        workflow = create_workflow()

        node = WorkflowNode.objects.create(
            workflow=workflow,
            name="Finance Review",
            node_type=WorkflowNode.ACTION,
            configuration={
                "title": "Review Purchase Order",
                "description": "Finance approval required",
                "priority": 80,
            },
        )

        instance = WorkflowInstance.objects.create(
            workflow=workflow,
            organization=workflow.organization,
            started_by=workflow.created_by,
        )

        token = WorkflowToken.objects.create(
            instance=instance,
            node=node,
        )

        context = WorkflowExecutionContext(instance)

        executor = ExecutorFactory.get_executor(
            WorkflowNode.ACTION,
        )(context, token)

        executor.execute()

        action = ActionItem.objects.get()

        self.assertEqual(
            action.title,
            "Review Purchase Order",
        )

        self.assertEqual(
            action.source_type,
            "workflow",
        )

        self.assertEqual(
            action.workflow_instance,
            instance,
        )

        outputs = context.get("action_outputs")

        self.assertEqual(
            outputs[0]["action_id"],
            action.pk,
        )

        self.assertEqual(
            outputs[0]["status"],
            "open",
        )

    def test_approval_executor(self):

        workflow = create_workflow()

        node = WorkflowNode.objects.create(
            workflow=workflow,
            name="Finance Approval",
            node_type=WorkflowNode.APPROVAL,
            configuration={
                "title": "Approve Vendor Payment",
                "description": "Finance approval required",
                "priority": 90,
            },
        )

        instance = WorkflowInstance.objects.create(
            workflow=workflow,
            organization=workflow.organization,
            started_by=workflow.created_by,
        )

        token = WorkflowToken.objects.create(
            instance=instance,
            node=node,
        )

        context = WorkflowExecutionContext(instance)

        executor = ExecutorFactory.get_executor(
            WorkflowNode.APPROVAL,
        )(context, token)

        executor.execute()

        approval = ApprovalItem.objects.get()

        self.assertEqual(
            approval.title,
            "Approve Vendor Payment",
        )

        self.assertEqual(
            approval.source_type,
            "workflow",
        )

        self.assertEqual(
            approval.workflow_instance,
            instance,
        )

        outputs = context.get(
            "approval_outputs"
        )

        self.assertEqual(
            outputs[0]["approval_id"],
            approval.pk,
        )

        self.assertEqual(
            outputs[0]["status"],
            approval.status,
        )

    def test_ai_executor(self):
        self.assertTrue(
            self._execute(
                WorkflowNode.AI
            ).get("ai_results")[0]["processed"]
        )

    def test_notification_executor(self):

        workflow = create_workflow()

        node = WorkflowNode.objects.create(
            workflow=workflow,
            name="Finance Notification",
            node_type=WorkflowNode.NOTIFICATION,
            configuration={
                "message": "Finance has been notified",
                "type": "system",
                "channel": "in_app",
            },
        )

        instance = WorkflowInstance.objects.create(
            workflow=workflow,
            organization=workflow.organization,
            started_by=workflow.created_by,
        )

        token = WorkflowToken.objects.create(
            instance=instance,
            node=node,
        )

        context = WorkflowExecutionContext(instance)

        executor = ExecutorFactory.get_executor(
            WorkflowNode.NOTIFICATION,
        )(context, token)

        executor.execute()

        notification = Notification.objects.get()

        self.assertEqual(
            notification.message,
            "Finance has been notified",
        )

        self.assertEqual(
            notification.source_type,
            "workflow",
        )

        self.assertEqual(
            notification.workflow_instance,
            instance,
        )

        self.assertEqual(
            notification.status,
            "sent",
        )

        outputs = context.get(
            "notification_outputs"
        )

        self.assertEqual(
            outputs[0]["notification_id"],
            notification.pk,
        )

        self.assertEqual(
            outputs[0]["status"],
            "sent",
        )

    def test_wait_executor(self):

        workflow = create_workflow()

        node = WorkflowNode.objects.create(
            workflow=workflow,
            name="Wait Node",
            node_type=WorkflowNode.WAIT,
            configuration={
                "reason": "approval_timeout",
            },
        )

        instance = WorkflowInstance.objects.create(
            workflow=workflow,
            organization=workflow.organization,
            started_by=workflow.created_by,
        )

        token = WorkflowToken.objects.create(
            instance=instance,
            node=node,
        )

        context = WorkflowExecutionContext(instance)

        executor = ExecutorFactory.get_executor(
            WorkflowNode.WAIT,
        )(context, token)

        result = executor.execute()

        token.refresh_from_db()

        self.assertFalse(result)

        self.assertEqual(
            token.status,
            WorkflowToken.STATUS_WAITING,
        )

        self.assertEqual(
            token.wait_reason,
            "approval_timeout",
        )

        outputs = context.get(
            "wait_outputs"
        )

        self.assertEqual(
            outputs[0]["status"],
            WorkflowToken.STATUS_WAITING,
        )