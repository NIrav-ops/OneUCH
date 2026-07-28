from django.test import TestCase

from platform_core.events.base import (
    DomainEvent,
)

from platform_core.events.handler import (
    EventHandler,
)

from platform_core.events.manager import (
    EventPipelineManager,
)


class DummyHandler(EventHandler):

    def __init__(self):

        self.executed = False

    def handle(
        self,
        event,
    ):

        self.executed = True


class PipelineTests(TestCase):

    def test_pipeline(self):

        manager = EventPipelineManager()

        handler = DummyHandler()

        manager.register(
            handler,
        )

        manager.execute(

            DomainEvent(

                name="knowledge.created",

                payload={},

            )

        )

        self.assertTrue(
            handler.executed,
        )

    def test_multiple_handlers(self):

        manager = EventPipelineManager()

        one = DummyHandler()

        two = DummyHandler()

        manager.register(one)

        manager.register(two)

        manager.execute(

            DomainEvent(

                name="workflow.completed",

                payload={},

            )

        )

        self.assertTrue(one.executed)

        self.assertTrue(two.executed)

    def test_result_success(self):

        manager = EventPipelineManager()

        result = manager.execute(

            DomainEvent(

                name="demo",

                payload={},

            )

        )

        self.assertTrue(
            result.success,
        )