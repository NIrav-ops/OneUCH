class AuditRepository:
    """
    Temporary in-memory repository.

    Phase 11:
        Will be replaced with
        AuditLog model.
    """

    _events = []

    @classmethod
    def save(
        cls,
        audit_event,
    ):

        cls._events.append(
            audit_event,
        )

    @classmethod
    def all(
        cls,
    ):

        return list(
            cls._events,
        )

    @classmethod
    def clear(
        cls,
    ):

        cls._events.clear()

    @classmethod
    def count(
        cls,
    ):

        return len(
            cls._events,
        )