from platform_core.events.subscriber_base import BaseSubscriber


class LoggingSubscriber(BaseSubscriber):

    event_name = "knowledge.created"

    def __init__(self):
        self.called = False

    def handle(self, event):
        self.called = True


class WorkflowAuditSubscriber(BaseSubscriber):

    event_name = "workflow.completed"

    def __init__(self):
        self.called = False

    def handle(self, event):
        self.called = True