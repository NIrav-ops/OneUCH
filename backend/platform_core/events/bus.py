class EventBus:

    _subscribers = {}

    @classmethod
    def subscribe(
        cls,
        event_name,
        subscriber,
    ):

        cls._subscribers.setdefault(
            event_name,
            [],
        ).append(
            subscriber,
        )

    @classmethod
    def publish(
        cls,
        event,
    ):

        for subscriber in cls._subscribers.get(
            event.name,
            [],
        ):

            subscriber.handle(
                event,
            )