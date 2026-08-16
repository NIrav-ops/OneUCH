from workflow.services.executors.base import (
    BaseNodeExecutor,
)

from workflow.services.webhook.service import (
    WebhookService,
)

from workflow.services.runtime_result import (
    ExecutionResult,
)

class WebhookNodeExecutor(BaseNodeExecutor):

    def execute(self):

        configuration = (
            self.token.node.configuration or {}
        )

        response = WebhookService(
                        self.context
                    ).execute(
                        configuration
                    )

        outputs = self.context.get(
            "webhook_outputs",
            [],
        )

        outputs.append(
            {
                "node": self.token.node.name,

                "status_code": response["status_code"],

                "response": response["body"],

                "url": configuration.get(
                    "url",
            ),
        }
    )

        self.context.set(
            "webhook_outputs",
            outputs,
        )

        return ExecutionResult(
            success=response["success"],
            outputs={
                "webhook": response,
            },
            message="Webhook executed successfully."
        )