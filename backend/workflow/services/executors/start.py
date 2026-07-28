from workflow.services.executors.base import BaseNodeExecutor


class StartNodeExecutor(BaseNodeExecutor):

    def execute(self):

        self.context.set(
            "_started",
            True,
        )

        return True