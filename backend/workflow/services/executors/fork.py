from workflow.services.executors.base import BaseNodeExecutor


class ForkNodeExecutor(BaseNodeExecutor):

    def execute(self):
        return True