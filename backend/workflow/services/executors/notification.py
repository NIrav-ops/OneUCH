from workflow.services.executors.base import BaseNodeExecutor
from workflow.services.integrations.notification_service import (
    NotificationIntegrationService,
)


class NotificationNodeExecutor(BaseNodeExecutor):

    def execute(self):

        instance = self.context.instance
        node = self.token.node

        notification = NotificationIntegrationService.create_notification(
            organization=instance.organization,
            user=instance.started_by,
            workflow_instance=instance,
            workflow_node=node,
            title=node.name,
            message=node.configuration.get(
                "message",
                f"Workflow notification from '{node.name}'",
            ),
            notification_type=node.configuration.get(
                "type",
                "system",
            ),
            channel=node.configuration.get(
                "channel",
                "in_app",
            ),
            metadata={
                "workflow_id": str(instance.workflow.id),
                "workflow_name": instance.workflow.name,
                "node_id": str(node.id),
                "node_name": node.name,
            },
        )

        NotificationIntegrationService.mark_sent(
            notification
        )

        outputs = self.context.get(
            "notification_outputs",
            []
        )

        outputs.append(
            {
                "notification_id": notification.pk,
                "status": notification.status,
                "channel": notification.channel,
                "node": node.name,
            }
        )

        self.context.set(
            "notification_outputs",
            outputs,
        )

        return True