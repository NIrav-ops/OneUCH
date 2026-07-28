from django.test import TestCase

from platform_core.events.base import DomainEvent

from platform_core.events.subscriptions import (
    SubscriptionRegistry,
)

from platform_core.events.subscription_manager import (
    SubscriptionManager,
)

from platform_core.events.subscribers import (
    LoggingSubscriber,
)


class SubscriptionTests(TestCase):

    def tearDown(self):

        SubscriptionRegistry.clear()

    def test_register(self):

        manager = SubscriptionManager()

        manager.register(
            LoggingSubscriber(),
        )

        self.assertEqual(
            SubscriptionRegistry.count(),
            1,
        )

    def test_dispatch(self):

        manager = SubscriptionManager()

        subscriber = LoggingSubscriber()

        manager.register(
            subscriber,
        )

        manager.dispatch(
            DomainEvent(
                name="knowledge.created",
                payload={},
            )
        )

        self.assertTrue(
            subscriber.called,
        )

    def test_no_subscribers(self):

        manager = SubscriptionManager()

        manager.dispatch(
            DomainEvent(
                name="unknown.event",
                payload={},
            )
        )

        self.assertEqual(
            SubscriptionRegistry.count(),
            0,
        )

    def test_multiple_subscribers(self):

        manager = SubscriptionManager()

        one = LoggingSubscriber()

        two = LoggingSubscriber()

        manager.register(one)
        manager.register(two)

        manager.dispatch(
            DomainEvent(
                name="knowledge.created",
                payload={},
            )
        )

        self.assertTrue(one.called)
        self.assertTrue(two.called)