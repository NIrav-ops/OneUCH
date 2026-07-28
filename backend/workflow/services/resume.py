from workflow.services.context import WorkflowExecutionContext

from workflow.services.ai.review import (
    AIHumanReviewResolution,
)


class WorkflowResumeManager:
    """
    Enterprise workflow resume coordinator.

    Responsible for preparing a workflow to continue
    after a human review decision.

    This class intentionally DOES NOT:

    - execute workflow nodes
    - activate execution tokens
    - call AI providers
    - persist database state

    It only updates the runtime execution context.
    """

    @classmethod
    def apply_resolution(
        cls,
        context: WorkflowExecutionContext,
        resolution: AIHumanReviewResolution,
    ) -> WorkflowExecutionContext:

        if not isinstance(
            resolution,
            AIHumanReviewResolution,
        ):
            raise TypeError(
                "resolution must be an AIHumanReviewResolution."
            )

        context.set_review_resolution(
            resolution
        )

        context.clear_pending_review()

        context.resume()

        context.set(
            "workflow_ready_to_resume",
            resolution.can_continue,
        )

        return context