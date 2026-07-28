from knowledge.services.workflow.base_workflow_engine import (
    BaseWorkflowEngine,
)


class FollowupEngine(
    BaseWorkflowEngine,
):

    category = "followups"

    def build(
        self,
        *,
        organization,
    ):

        return {

            "required": 0,

            "completed": 0,

            "pending": 0,

        }