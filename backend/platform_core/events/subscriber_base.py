class BaseSubscriber:

    event_name = ""

    def handle(
        self,
        event,
    ):
        raise NotImplementedError