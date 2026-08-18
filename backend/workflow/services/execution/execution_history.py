from workflow.models import WorkflowExecutionLog


class WorkflowExecutionHistoryError(
    ValueError
):
    """
    Raised when an execution-history mutation is attempted
    through the application service boundary.
    """

    pass


class WorkflowExecutionHistoryService:
    """
    Controlled access boundary for workflow execution history.

    Execution history is append-only.

    Creation is delegated to WorkflowExecutionEventService.

    This service intentionally exposes no update/delete operation.
    """

    @staticmethod
    def get_for_instance(
        instance,
    ):
        """
        Return execution history for one runtime instance.

        History is ordered oldest-first because execution history
        represents a timeline rather than a reverse activity feed.
        """

        return (
            WorkflowExecutionLog.objects
            .filter(
                instance=instance,
            )
            .select_related(
                "node",
            )
            .order_by(
                "created_at",
                "id",
            )
        )

    @staticmethod
    def assert_read_only():
        """
        Explicit documentation/guard for callers that need to
        communicate the history mutation policy.

        No mutation methods are intentionally provided.
        """

        return True