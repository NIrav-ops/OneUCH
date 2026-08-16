from workflow.services.executors.base import BaseNodeExecutor


class ConditionExecutor(BaseNodeExecutor):
    """
    Condition nodes do not execute business logic.

    Their only purpose is to act as a routing decision point.
    """

    def execute(self):
        # Routing is handled by WorkflowRuntimeEngine.get_next_node()
        return None