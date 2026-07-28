from workflow.models import WorkflowNode

from workflow.services.executors.start import (
    StartNodeExecutor,
)

from workflow.services.executors.end import (
    EndNodeExecutor,
)

from workflow.services.executors.action import (
    ActionNodeExecutor,
)
from workflow.services.executors.approval import (
    ApprovalNodeExecutor,
)
from workflow.services.executors.ai import (
    AINodeExecutor,
)
from workflow.services.executors.notification import (
    NotificationNodeExecutor,
)
from workflow.services.executors.wait import (
    WaitNodeExecutor,
)


class ExecutorFactory:

    EXECUTORS = {

        WorkflowNode.START: StartNodeExecutor,
        WorkflowNode.END: EndNodeExecutor,
        WorkflowNode.ACTION: ActionNodeExecutor,
        WorkflowNode.APPROVAL: ApprovalNodeExecutor,
        WorkflowNode.AI: AINodeExecutor,
        WorkflowNode.NOTIFICATION: NotificationNodeExecutor,
        WorkflowNode.WAIT: WaitNodeExecutor,
    }

    @classmethod
    def get_executor(
        cls,
        node_type,
    ):

        executor = cls.EXECUTORS.get(
            node_type
        )

        if executor is None:

            raise ValueError(
                f"No executor registered for '{node_type}'"
            )

        return executor