from platform_core.audit.repository import (
    AuditRepository,
)


class AuditService:

    def events(
        self,
    ):

        return AuditRepository.all()

    def count(
        self,
    ):

        return AuditRepository.count()

    def clear(
        self,
    ):

        AuditRepository.clear()