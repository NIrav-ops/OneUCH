from platform_core.events.result import (
    EventResult,
)


class EventPipeline:

    def __init__(self):

        self.handlers = []

    def add_handler(
        self,
        handler,
    ):

        self.handlers.append(
            handler,
        )

    def process(
        self,
        event,
    ):

        result = EventResult()

        for handler in self.handlers:

            handler.handle(
                event,
            )

        return result