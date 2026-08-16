from .base import BaseNodeExecutor


class SubWorkflowContext:

    def __init__(self, parent_context):

        self.parent = parent_context

    def create_child(self):

        return dict(
            self.parent.data
        )

    def merge(self, child_context):

        merged = dict(
            self.parent.data
        )

        merged.update(child_context)

        return merged

from workflow.models import (
    WorkflowDefinition,
    WorkflowInstance,
)


class SubWorkflowExecutor(BaseNodeExecutor):

    def execute(self):

        configuration = self.token.node.configuration or {}

        workflow_id = configuration.get("workflow_id")

        if not workflow_id:
            raise ValueError(
                "Subworkflow node requires workflow_id."
            )

        workflow = WorkflowDefinition.objects.get(
            pk=workflow_id
        )

        child_instance = WorkflowInstance.objects.create(
            workflow=workflow,
            organization=self.organization,
            started_by=self.user,
            context=self.context.data,
        )

        outputs = self.context.get(
            "subworkflow_outputs",
            [],
        )

        outputs.append(
            {
                "node": self.token.node.name,
                "workflow": workflow.name,
                "instance": str(child_instance.pk),
            }
        )

        self.context.set(
            "subworkflow_outputs",
            outputs,
        )

        return True