from workflow.models import (
    WorkflowNode,
    WorkflowToken,
)

from workflow.services.context import (
    WorkflowExecutionContext,
)

from workflow.services.executors import (
    ExecutorFactory,
)

from workflow.services.runtime_repository import (
    WorkflowRuntimeRepository,
)

from workflow.services.execution import (
    WorkflowExecutionEventService,
)


class WorkflowRuntimeEngine:
    """
    Enterprise workflow runtime engine.

    Responsible for orchestrating workflow execution.

    Responsibilities:
    - create runtime tokens
    - dispatch node executors
    - advance workflow tokens
    - stop execution when runtime becomes suspended

    This engine intentionally does NOT:

    - execute AI directly
    - resolve approvals
    - resume suspended workflows
    """

    def __init__(self, instance):

        self.instance = instance

        self.context = WorkflowExecutionContext(
            instance
        )

    def get_start_node(self):

        return WorkflowNode.objects.get(
            workflow=self.instance.workflow,
            node_type=WorkflowNode.START,
        )

    def get_next_node(self, node):

        transition = node.outgoing.first()

        if transition is None:
            return None

        return transition.target

    def execute_node(self, token):

        executor_cls = ExecutorFactory.get_executor(
            token.node.node_type
        )

        executor = executor_cls(
            self.context,
            token,
        )

        executor.execute()

        token.status = WorkflowToken.STATUS_COMPLETED

        WorkflowRuntimeRepository.token.save(
            token
        )

        self.context.save()

    def advance(self, token):

        if self.context.is_suspended:
            return None

        next_node = self.get_next_node(
            token.node
        )

        if next_node is None:
            return None

        return WorkflowRuntimeRepository.token.create(
            instance=self.instance,
            node=next_node,
        )

    def run(self):

        WorkflowExecutionEventService.record(
            instance=self.instance,
            event=WorkflowExecutionEventService.WORKFLOW_STARTED,
        )

        current = WorkflowRuntimeRepository.token.create(
            instance=self.instance,
            node=self.get_start_node(),
        )

        while current:

            if self.context.is_suspended:

                WorkflowExecutionEventService.record(
                    instance=self.instance,
                    node=current.node,
                    event=WorkflowExecutionEventService.WORKFLOW_SUSPENDED,
                )

                break

            WorkflowExecutionEventService.record(
                instance=self.instance,
                node=current.node,
                event=WorkflowExecutionEventService.NODE_STARTED,
            )

            self.execute_node(
                current
            )

            WorkflowExecutionEventService.record(
                instance=self.instance,
                node=current.node,
                event=WorkflowExecutionEventService.NODE_COMPLETED,
            )

            if self.context.is_suspended:

                WorkflowExecutionEventService.record(
                    instance=self.instance,
                    node=current.node,
                    event=WorkflowExecutionEventService.WORKFLOW_SUSPENDED,
                )

                break

            current = self.advance(
                current
            )

        if not self.context.is_suspended:

            WorkflowExecutionEventService.record(
                instance=self.instance,
                event=WorkflowExecutionEventService.WORKFLOW_COMPLETED,
            )

        return self.instance