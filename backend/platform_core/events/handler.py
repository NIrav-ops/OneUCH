class EventHandler:
    """
    Base class for every
    enterprise event handler.
    """

    def handle(
        self,
        event,
    ):
        raise NotImplementedError