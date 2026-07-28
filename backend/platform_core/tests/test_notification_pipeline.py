from django.test import TestCase

from platform_core.events.base import (
    DomainEvent,
)

from platform_core.notifications.repository import (
    NotificationRepository,
)

from platform_core.notifications.subscriber import (
    KnowledgeNotificationSubscriber,
)


class NotificationPipelineTests(TestCase):

    def tearDown(self):

        NotificationRepository.clear()

    def test_notification_created(self):

        subscriber = KnowledgeNotificationSubscriber()

        subscriber.handle(

            DomainEvent(

                name="knowledge.created",

                payload={

                    "customer": "Google",

                },

            )

        )

        self.assertEqual(

            NotificationRepository.count(),

            1,

        )

    def test_title(self):

        subscriber = KnowledgeNotificationSubscriber()

        subscriber.handle(

            DomainEvent(

                name="knowledge.created",

                payload={},

            )

        )

        notification = NotificationRepository.all()[0]

        self.assertEqual(

            notification.title,

            "knowledge.created",

        )

    def test_payload(self):

        subscriber = KnowledgeNotificationSubscriber()

        subscriber.handle(

            DomainEvent(

                name="knowledge.created",

                payload={

                    "id": 10,

                },

            )

        )

        notification = NotificationRepository.all()[0]

        self.assertEqual(

            notification.payload["id"],

            10,

        )

    def test_clear(self):

        subscriber = KnowledgeNotificationSubscriber()

        subscriber.handle(

            DomainEvent(

                name="knowledge.created",

                payload={},

            )

        )

        NotificationRepository.clear()

        self.assertEqual(

            NotificationRepository.count(),

            0,

        )