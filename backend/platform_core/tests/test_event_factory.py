from django.test import TestCase

from platform_core.events.factory import (
    EventFactory,
)

from platform_core.events.names import (
    KNOWLEDGE_CREATED,
)


class EventFactoryTests(TestCase):

    def test_factory(self):

        event = EventFactory.create(

            name=KNOWLEDGE_CREATED,

            payload={

                "id": 1,

            },

        )

        self.assertEqual(

            event.name,

            KNOWLEDGE_CREATED,

        )

        self.assertEqual(

            event.payload["id"],

            1,

        )