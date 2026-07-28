from workflow.services.runtime_repository import (
    WorkflowRuntimeRepository,
)


class WorkflowExecutionEventService:
    """
    Records workflow runtime events.

    This service centralizes execution logging so the runtime
    engine and node executors never manipulate
    WorkflowExecutionLog directly.
    """

    NODE_STARTED = "node_started"
    NODE_COMPLETED = "node_completed"
    NODE_FAILED = "node_failed"

    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"

    WORKFLOW_SUSPENDED = "workflow_suspended"
    WORKFLOW_RESUMED = "workflow_resumed"

    @classmethod
    def record(
        cls,
        *,
        instance,
        event,
        node=None,
        details=None,
    ):

        return WorkflowRuntimeRepository.log.create(
            instance=instance,
            node=node,
            event=event,
            details=details or {},
        )