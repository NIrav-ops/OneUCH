from platform_core.events.registry import (
    EventRegistry,
)


class EventPublisher:

    def publish(
        self,
        event,
    ):

        EventRegistry.register(
            event,
        )

        return event