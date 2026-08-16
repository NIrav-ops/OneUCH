from django.utils import timezone

from workflow.models import WorkflowToken
from workflow.services.executors.base import BaseNodeExecutor


class WaitNodeExecutor(BaseNodeExecutor):

    def execute(self):

        token = self.token
        node = token.node

        configuration = node.configuration or {}

        token.status = WorkflowToken.STATUS_WAITING

        token.wait_until = configuration.get(
            "wait_until"
        )

        token.wait_reason = configuration.get(
            "reason",
            "workflow_wait",
        )

        configuration.setdefault(
            "policy",
            "datetime",
        )

        token.wait_configuration = configuration

        token.save(
            update_fields=[
                "status",
                "wait_until",
                "wait_reason",
                "wait_configuration",
            ]
        )

        waits = self.context.get(
            "wait_outputs",
            []
        )

        waits.append(
            {
                "token_id": str(token.pk),
                "status": token.status,
                "reason": token.wait_reason,
            }
        )

        self.context.set(
            "wait_outputs",
            waits,
        )

        return False