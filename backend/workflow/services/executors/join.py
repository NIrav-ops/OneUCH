from workflow.services.executors.base import BaseNodeExecutor


class JoinNodeExecutor(BaseNodeExecutor):

    def execute(self):
        return True