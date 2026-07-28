from platform_core.events.publisher import (
    EventPublisher,
)

from platform_core.events.factory import (
    EventFactory,
)

from platform_core.events.names import (
    TIMELINE_UPDATED,
)


class TimelineEventPublisher:

    def updated(
        self,
        timeline_id,
    ):

        EventPublisher().publish(

            EventFactory.create(

                name=TIMELINE_UPDATED,

                payload={

                    "timeline_id": timeline_id,

                },

            )

        )