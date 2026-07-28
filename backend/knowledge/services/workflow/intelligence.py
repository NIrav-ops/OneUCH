from knowledge.services.workflow.execution_dashboard import (
    ExecutionDashboardService,
)


class WorkflowIntelligenceService:

    def __init__(self):

        self.dashboard = (
            ExecutionDashboardService()
        )

    def build(
        self,
        *,
        organization,
    ):

        dashboard = self.dashboard.build(
            organization=organization,
        )

        return {

            "dashboard": dashboard,

        }