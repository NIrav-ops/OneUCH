from workflow.services.context import (
    WorkflowExecutionContext,
)

from workflow.services.ai.review import (
    AIHumanReviewResolution,
)


class WorkflowResumeManager:
    """
    Enterprise workflow resume coordinator.

    Responsible only for applying a completed human-review
    resolution to the persisted workflow execution context.

    This class does NOT:

    - execute workflow nodes
    - create or activate runtime tokens
    - call AI providers
    - resolve workflow definitions
    - change workflow versions
    - control runtime execution

    Actual runtime continuation is handled by
    WorkflowRuntimeEngine.resume().
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
                "resolution must be an "
                "AIHumanReviewResolution."
            )

        #
        # Persist the completed human-review
        # decision into the execution context.
        #

        context.set_review_resolution(
            resolution
        )

        #
        # Remove transient review-request state.
        #

        context.clear_pending_review()

        #
        # Clear workflow suspension.
        #

        context.resume()

        #
        # Tell the runtime that the workflow is
        # eligible to continue.
        #

        context.set(
            "workflow_ready_to_resume",
            resolution.can_continue,
        )

        #
        # Persist the updated runtime context.
        #
        # This is important because resume may occur
        # in a different request/process from the one
        # that originally suspended the workflow.
        #

        context.save()

        return context