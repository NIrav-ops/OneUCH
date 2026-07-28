from django.test import TestCase

from workflow.models import (
    WorkflowInstance,
)

from workflow.services.context import (
    WorkflowExecutionContext,
)

from workflow.tests.utils import (
    create_workflow,
)


class WorkflowExecutionContextSuspensionTests(
    TestCase
):

    def _build_context(self):

        workflow = create_workflow()

        instance = (
            WorkflowInstance.objects.create(
                workflow=workflow,
                organization=(
                    workflow.organization
                ),
                started_by=(
                    workflow.created_by
                ),
                context={},
            )
        )

        return WorkflowExecutionContext(
            instance
        )

    def test_context_can_be_suspended(self):

        context = self._build_context()

        context.suspend(
            reason="AI_HUMAN_REVIEW",
            metadata={
                "review_id": "REVIEW-100",
            },
        )

        self.assertTrue(
            context.is_suspended
        )

        self.assertTrue(
            context.get(
                "workflow_suspended"
            )
        )

        self.assertEqual(
            context.get(
                "suspension_reason"
            ),
            "AI_HUMAN_REVIEW",
        )

        self.assertEqual(
            context.get(
                "suspension_metadata"
            )["review_id"],
            "REVIEW-100",
        )

    def test_context_can_be_resumed(self):

        context = self._build_context()

        context.suspend(
            reason="AI_HUMAN_REVIEW",
        )

        context.resume()

        self.assertFalse(
            context.is_suspended
        )

        self.assertFalse(
            context.get(
                "workflow_suspended"
            )
        )

        self.assertIsNone(
            context.get(
                "suspension_reason"
            )
        )

        self.assertEqual(
            context.get(
                "suspension_metadata"
            ),
            {},
        )

    def test_context_is_not_suspended_by_default(
        self,
    ):

        context = self._build_context()

        self.assertFalse(
            context.is_suspended
        )

    def test_review_resolution_properties(
        self,
    ):

        context = self._build_context()

        self.assertFalse(
            context.review_completed
        )

        context.set_review_resolution(
            {
                "approved": True,
                "rejected": False,
            }
        )

        self.assertTrue(
            context.review_completed
        )

        self.assertTrue(
            context.review_approved
        )

        self.assertFalse(
            context.review_rejected
        )    