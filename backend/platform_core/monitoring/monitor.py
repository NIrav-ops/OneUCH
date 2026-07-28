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

    def check(self):

        metrics = PlatformMetrics().collect()

        MonitoringService().report(

            HealthStatus(

                service="Platform",

                status="Healthy",

                details=metrics,

            )

        )

        return metrics