from platform_core.events.pipeline import (
    EventPipeline,
)


class EventPipelineManager:

    def __init__(self):

        self.pipeline = EventPipeline()

    def register(
        self,
        handler,
    ):

        self.pipeline.add_handler(
            handler,
        )

    def execute(
        self,
        event,
    ):

        return self.pipeline.process(
            event,
        )