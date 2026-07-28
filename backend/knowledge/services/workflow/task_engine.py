from knowledge.services.workflow.base_workflow_engine import (
    BaseWorkflowEngine,
)


class TaskEngine(
    BaseWorkflowEngine,
):

    category = "tasks"

    def build(
        self,
        *,
        organization,
    ):

        return {

            "total": 0,

            "pending": 0,

            "completed": 0,

            "overdue": 0,

        }