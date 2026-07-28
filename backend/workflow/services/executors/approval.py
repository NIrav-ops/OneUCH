from workflow.services.executors.base import BaseNodeExecutor
from workflow.services.integrations.approval_service import (
    ApprovalIntegrationService,
)


class ApprovalNodeExecutor(BaseNodeExecutor):

    def execute(self):

        config = self.token.node.configuration or {}

        approval = ApprovalIntegrationService.create_request(

            organization=self.token.instance.organization,

            workflow_instance=self.token.instance,

            title=config.get(
                "title",
                self.token.node.name,
            ),

            description=config.get(
                "description",
                "",
            ),

            priority=config.get(
                "priority",
                0,
            ),
        )

        outputs = self.context.get(
            "approval_outputs",
            [],
        )

        outputs.append(
            {
                "node": self.token.node.name,
                "approval_id": approval.pk,
                "status": approval.status,
                "title": approval.title,
            }
        )

        self.context.set(
            "approval_outputs",
            outputs,
        )

        return True