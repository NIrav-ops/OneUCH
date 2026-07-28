from platform_core.events.subscriber_base import (
    BaseSubscriber,
)

from platform_core.audit.event import (
    AuditEvent,
)

from platform_core.audit.repository import (
    AuditRepository,
)


class AuditSubscriber(
    BaseSubscriber,
):

    event_name = "knowledge.created"

    def handle(
        self,
        event,
    ):

        AuditRepository.save(

            AuditEvent(

                event_name=event.name,

                payload=event.payload,

            )

        )