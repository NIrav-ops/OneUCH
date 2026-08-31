from collections import deque


class HealthRepository:

    MAX_ENTRIES = 100

    _health = deque(
        maxlen=MAX_ENTRIES
    )

    @classmethod
    def save(cls, status):

        cls._health.append(status)

    @classmethod
    def all(cls):

        return list(cls._health)

    @classmethod
    def latest(cls):

        if not cls._health:
            return None

        return cls._health[-1]

    @classmethod
    def clear(cls):

        cls._health.clear()

    @classmethod
    def count(cls):

        return len(cls._health)
