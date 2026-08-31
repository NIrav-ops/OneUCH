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

from platform_core.observability.logger import (
    get_logger,
    log_event,
)


logger = get_logger(
    "oneuch.runtime.health"
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

            result = (
                settings.REDIS_CLIENT.ping()
            )

            if result is not True:

                return {
                    "status": "Unhealthy",
                    "error": "UnexpectedPingResponse",
                }

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

        health_status = HealthStatus(
            service="Platform",
            status=status,
            details=details,
        )

        MonitoringService().report(
            health_status
        )

        log_event(
            logger,
            (
                "info"
                if dependencies_healthy
                else "warning"
            ),
            "platform.health.checked",
            status=status,
            database_status=(
                dependencies[
                    "database"
                ][
                    "status"
                ]
            ),
            redis_status=(
                dependencies[
                    "redis"
                ][
                    "status"
                ]
            ),
        )

        return details
