from django.utils import timezone

from workflow.models import WorkflowInstance

from workflow.services.executors.base import BaseNodeExecutor


class EndNodeExecutor(BaseNodeExecutor):

    def execute(self):

        self.token.instance.status = WorkflowInstance.STATUS_COMPLETED

        self.token.instance.completed_at = timezone.now()

        self.token.instance.save(
            update_fields=[
                "status",
                "completed_at",
            ]
        )

        return True