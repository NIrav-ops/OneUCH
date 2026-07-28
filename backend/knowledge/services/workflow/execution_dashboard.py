from knowledge.services.workflow.task_engine import (
    TaskEngine,
)

from knowledge.services.workflow.followup_engine import (
    FollowupEngine,
)

from knowledge.services.workflow.approval_engine import (
    ApprovalEngine,
)


class ExecutionDashboardService:

    def __init__(self):

        self.tasks = TaskEngine()

        self.followups = FollowupEngine()

        self.approvals = ApprovalEngine()

    def build(
        self,
        *,
        organization,
    ):

        return {

            "tasks": self.tasks.build(
                organization=organization,
            ),

            "followups": self.followups.build(
                organization=organization,
            ),

            "approvals": self.approvals.build(
                organization=organization,
            ),

        }