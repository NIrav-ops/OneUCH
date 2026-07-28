from platform_core.events.subscriber_base import (
    BaseSubscriber,
)

from platform_core.notifications.event import (
    NotificationEvent,
)

from platform_core.notifications.repository import (
    NotificationRepository,
)

from platform_core.notifications.message import (
    NotificationMessage,
)


class KnowledgeNotificationSubscriber(
    BaseSubscriber,
):

    event_name = "knowledge.created"

    def handle(
        self,
        event,
    ):

        message = NotificationMessage.build(
            event,
        )

        NotificationRepository.save(

            NotificationEvent(

                title=message["title"],

                message=message["message"],

                event_name=event.name,

                payload=event.payload,

            )

        )