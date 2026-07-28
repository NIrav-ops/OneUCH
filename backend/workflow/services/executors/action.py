from workflow.services.executors.base import BaseNodeExecutor
from workflow.services.integrations.action_service import (
    ActionIntegrationService,
)


class ActionNodeExecutor(BaseNodeExecutor):

    def execute(self):

        config = self.token.node.configuration or {}

        action = ActionIntegrationService.create_action(
            
            organization=self.token.instance.organization,

            workflow_instance=self.token.instance,

            source_type="workflow",

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
            "action_outputs",
            [],
        )

        outputs.append(
            {
                "node": self.token.node.name,
                "action_id": action.pk,
                "status": action.status,
                "title": action.title,
            }
        )

        self.context.set(
            "action_outputs",
            outputs,
        )

        return True