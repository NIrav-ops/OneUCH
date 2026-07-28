class SubscriptionRegistry:

    _subscriptions = {}

    @classmethod
    def subscribe(
        cls,
        event_name,
        subscriber,
    ):

        cls._subscriptions.setdefault(
            event_name,
            [],
        ).append(
            subscriber,
        )

    @classmethod
    def subscribers(
        cls,
        event_name,
    ):

        return cls._subscriptions.get(
            event_name,
            [],
        )

    @classmethod
    def clear(
        cls,
    ):

        cls._subscriptions.clear()

    @classmethod
    def count(
        cls,
    ):

        return sum(
            len(v)
            for v in cls._subscriptions.values()
        )