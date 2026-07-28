class HealthRepository:

    _health = []

    @classmethod
    def save(cls, status):

        cls._health.append(status)

    @classmethod
    def all(cls):

        return list(cls._health)

    @classmethod
    def clear(cls):

        cls._health.clear()

    @classmethod
    def count(cls):

        return len(cls._health)