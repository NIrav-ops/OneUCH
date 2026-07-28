from django.test import TestCase

from workflow.models import WorkflowInstance

from workflow.services.context import WorkflowExecutionContext

from workflow.services.resume import WorkflowResumeManager

from workflow.services.ai.review import (
    AIHumanReviewResolution,
)

from workflow.tests.utils import create_workflow


class WorkflowResumeManagerTests(TestCase):

    def _build_context(self):

        workflow = create_workflow()

        instance = WorkflowInstance.objects.create(
            workflow=workflow,
            organization=workflow.organization,
            started_by=workflow.created_by,
            context={},
        )

        return WorkflowExecutionContext(
            instance
        )

    def test_resume_manager_prepares_workflow_for_resume(self):

        context = self._build_context()

        context.suspend(
            reason="AI_HUMAN_REVIEW"
        )

        context.set(
            "ai_review_pending",
            True,
        )

        resolution = AIHumanReviewResolution(
            review_id="REVIEW-100",
            approved=True,
            rejected=False,
            can_continue=True,
            reviewer="admin@example.com",
            comments="Approved",
            reason="Human review approved.",
        )

        WorkflowResumeManager.apply_resolution(
            context=context,
            resolution=resolution,
        )

        self.assertFalse(
            context.is_suspended
        )

        self.assertFalse(
            context.get(
                "ai_review_pending"
            )
        )

        self.assertTrue(
            context.review_completed
        )

        self.assertTrue(
            context.review_approved
        )

        self.assertTrue(
            context.get(
                "workflow_ready_to_resume"
            )
        )