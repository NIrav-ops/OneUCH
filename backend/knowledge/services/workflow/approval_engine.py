from knowledge.services.workflow.base_workflow_engine import (
    BaseWorkflowEngine,
)


class ApprovalEngine(
    BaseWorkflowEngine,
):

    category = "approvals"

    def build(
        self,
        *,
        organization,
    ):

        return {

            "pending": 0,

            "approved": 0,

            "rejected": 0,

        }