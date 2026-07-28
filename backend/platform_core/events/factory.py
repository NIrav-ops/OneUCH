from platform_core.events.base import (
    DomainEvent,
)


class EventFactory:

    @staticmethod
    def create(
        *,
        name,
        payload,
    ):

        return DomainEvent(

            name=name,

            payload=payload,

        )