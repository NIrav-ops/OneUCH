class EventRegistry:

    _events = {}

    @classmethod
    def register(
        cls,
        event,
    ):

        cls._events[event.name] = event

    @classmethod
    def all(cls):

        return dict(cls._events)

    @classmethod
    def clear(cls):

        cls._events.clear()