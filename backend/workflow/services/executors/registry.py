from workflow.models import WorkflowNode

from workflow.services.executors.action import ActionNodeExecutor
from workflow.services.executors.ai import AINodeExecutor
from workflow.services.executors.approval import ApprovalNodeExecutor
from workflow.services.executors.end import EndNodeExecutor
from workflow.services.executors.notification import NotificationNodeExecutor
from workflow.services.executors.script import ScriptNodeExecutor
from workflow.services.executors.start import StartNodeExecutor
from workflow.services.executors.wait import WaitNodeExecutor
from workflow.services.executors.webhook import WebhookNodeExecutor
from workflow.services.executors.subworkflow_executor import SubWorkflowExecutor
from workflow.services.executors.condition_executor import ConditionExecutor
from workflow.services.executors.fork import ForkNodeExecutor
from workflow.services.executors.join import JoinNodeExecutor


class ExecutorRegistry:

    EXECUTORS = {
        WorkflowNode.START: StartNodeExecutor,
        WorkflowNode.END: EndNodeExecutor,
        WorkflowNode.ACTION: ActionNodeExecutor,
        WorkflowNode.APPROVAL: ApprovalNodeExecutor,
        WorkflowNode.AI: AINodeExecutor,
        WorkflowNode.WAIT: WaitNodeExecutor,
        WorkflowNode.NOTIFICATION: NotificationNodeExecutor,
        WorkflowNode.SCRIPT: ScriptNodeExecutor,
        WorkflowNode.WEBHOOK: WebhookNodeExecutor,
        WorkflowNode.SUBWORKFLOW: SubWorkflowExecutor,
        WorkflowNode.CONDITION: ConditionExecutor,
        WorkflowNode.FORK: ForkNodeExecutor,
        WorkflowNode.JOIN: JoinNodeExecutor,
    }

    @classmethod
    def get_executor(cls, node_type):
        executor = cls.EXECUTORS.get(node_type)

        if executor is None:
            raise ValueError(
                f"No executor registered for node type '{node_type}'."
            )

        return executor