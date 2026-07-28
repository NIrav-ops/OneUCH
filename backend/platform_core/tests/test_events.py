from django.test import TestCase

from platform_core.events.base import (
    DomainEvent,
)

from platform_core.events.publisher import (
    EventPublisher,
)

from platform_core.events.registry import (
    EventRegistry,
)


class EventTests(TestCase):

    def tearDown(self):

        EventRegistry.clear()

    def test_publish(self):

        event = DomainEvent(

            name="knowledge.created",

            payload={},

        )

        EventPublisher().publish(
            event,
        )

        self.assertEqual(

            len(
                EventRegistry.all(),
            ),

            1,

        )

    def test_event_name(self):

        event = DomainEvent(

            name="workflow.completed",

            payload={},

        )

        self.assertEqual(

            event.name,

            "workflow.completed",

        )

    def test_payload(self):

        event = DomainEvent(

            name="knowledge.created",

            payload={

                "id": 1,

            },

        )

        self.assertEqual(

            event.payload["id"],

            1,

        )