from django.test import TestCase

from workflow.models import WorkflowInstance

from workflow.services.context import (
    WorkflowExecutionContext,
)

from workflow.tests.utils import create_workflow


class WorkflowExecutionContextTests(TestCase):

    def test_set_variable(self):

        workflow = create_workflow()

        instance = WorkflowInstance.objects.create(
            workflow=workflow,
            organization=workflow.organization,
        )

        context = WorkflowExecutionContext(
            instance
        )

        context.set(
            "customer",
            "Cyberllix",
        )

        self.assertEqual(
            context.get("customer"),
            "Cyberllix",
        )

    def test_update_variables(self):

        workflow = create_workflow()

        instance = WorkflowInstance.objects.create(
            workflow=workflow,
            organization=workflow.organization,
        )

        context = WorkflowExecutionContext(
            instance
        )

        context.update(
            {
                "amount": 5000,
                "currency": "INR",
            }
        )

        self.assertEqual(
            context.get("amount"),
            5000,
        )

    def test_remove_variable(self):

        workflow = create_workflow()

        instance = WorkflowInstance.objects.create(
            workflow=workflow,
            organization=workflow.organization,
        )

        context = WorkflowExecutionContext(
            instance
        )

        context.set(
            "status",
            "pending",
        )

        context.remove(
            "status"
        )

        self.assertFalse(
            context.exists(
                "status"
            )
        )

    def test_save_context(self):

        workflow = create_workflow()

        instance = WorkflowInstance.objects.create(
            workflow=workflow,
            organization=workflow.organization,
        )

        context = WorkflowExecutionContext(
            instance
        )

        context.set(
            "invoice",
            "INV001",
        )

        context.save()

        instance.refresh_from_db()

        self.assertEqual(
            instance.context["invoice"],
            "INV001",
        )