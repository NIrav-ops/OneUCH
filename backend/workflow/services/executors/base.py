from abc import ABC, abstractmethod


class BaseNodeExecutor(ABC):

    def __init__(self, context, token):

        self.context = context
        self.token = token

        # Runtime shortcuts
        self.instance = context.instance
        self.workflow = context.instance.workflow
        self.organization = context.instance.organization
        self.user = context.instance.started_by

    @abstractmethod
    def execute(self):
        """
        Execute the current node.
        """
        raise NotImplementedError