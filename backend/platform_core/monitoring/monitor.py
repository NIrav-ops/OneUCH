from django.conf import settings
from django.db import connection

from platform_core.monitoring.health import (
    HealthStatus,
)

from platform_core.monitoring.metrics import (
    PlatformMetrics,
)

from platform_core.monitoring.service import (
    MonitoringService,
)


class PlatformMonitor:

    @staticmethod
    def _check_database():

        try:

            connection.ensure_connection()

            with connection.cursor() as cursor:

                cursor.execute("SELECT 1")

                cursor.fetchone()

            return {
                "status": "Healthy",
            }

        except Exception as exc:

            return {
                "status": "Unhealthy",
                "error": exc.__class__.__name__,
            }

    @staticmethod
    def _check_redis():

        try:

            settings.REDIS_CLIENT.ping()

            return {
                "status": "Healthy",
            }

        except Exception as exc:

            return {
                "status": "Unhealthy",
                "error": exc.__class__.__name__,
            }

    def check(self):

        metrics = PlatformMetrics().collect()

        dependencies = {
            "database": self._check_database(),
            "redis": self._check_redis(),
        }

        dependencies_healthy = all(
            dependency["status"] == "Healthy"
            for dependency in dependencies.values()
        )

        status = (
            "Healthy"
            if dependencies_healthy
            else "Degraded"
        )

        details = {
            **metrics,
            "dependencies": dependencies,
        }

        MonitoringService().report(
            HealthStatus(
                service="Platform",
                status=status,
                details=details,
            )
        )

        return details
