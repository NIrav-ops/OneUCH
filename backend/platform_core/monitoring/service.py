from platform_core.monitoring.repository import (
    HealthRepository,
)


class MonitoringService:

    def report(
        self,
        status,
    ):

        HealthRepository.save(
            status,
        )

    def all(self):

        return HealthRepository.all()

    def clear(self):

        HealthRepository.clear()

    def count(self):

        return HealthRepository.count()