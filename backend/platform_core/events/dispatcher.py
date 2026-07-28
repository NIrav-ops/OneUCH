from platform_core.events.bus import (
    EventBus,
)


class EventDispatcher:

    def dispatch(
        self,
        event,
    ):

        EventBus.publish(
            event,
        )

        return event