from platform_core.events.publisher import (
    EventPublisher,
)

from platform_core.events.factory import (
    EventFactory,
)

from platform_core.events.names import (
    CUSTOMER_UPDATED,
)


class CustomerEventPublisher:

    def updated(
        self,
        customer_id,
    ):

        EventPublisher().publish(

            EventFactory.create(

                name=CUSTOMER_UPDATED,

                payload={

                    "customer_id": customer_id,

                },

            )

        )