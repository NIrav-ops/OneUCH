from platform_core.events.subscriptions import (
    SubscriptionRegistry,
)


class SubscriptionManager:

    def register(
        self,
        subscriber,
    ):

        SubscriptionRegistry.subscribe(
            subscriber.event_name,
            subscriber,
        )

    def dispatch(
        self,
        event,
    ):

        for subscriber in SubscriptionRegistry.subscribers(
            event.name,
        ):

            subscriber.handle(
                event,
            )