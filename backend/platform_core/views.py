from rest_framework.permissions import (
    IsAuthenticated,
)

from platform_core.monitoring.monitor import (
    PlatformMonitor,
)

from platform_core.monitoring.repository import (
    HealthRepository,
)

from platform_core.configuration.repository import (
    ConfigurationRepository,
)

from platform_core.jobs.repository import (
    JobRepository,
)

from platform_core.scheduler.repository import (
    ScheduleRepository,
)

from platform_core.api.base import EnterpriseAPIView


class PlatformHealthAPIView(EnterpriseAPIView):

    def get(self, request):

        PlatformMonitor().check()

        health = HealthRepository.all()[-1]

        return self.success(
            message="Platform health retrieved successfully.",
            data={
                "service": health.service,
                "status": health.status,
                "details": health.details,
            },
        )

class PlatformMetricsAPIView(EnterpriseAPIView):

    def get(self, request):

        PlatformMonitor().check()

        return self.success(
            message="Platform metrics retrieved successfully.",
            data=HealthRepository.all()[-1].details
        )

class PlatformConfigurationAPIView(EnterpriseAPIView):

    def get(self, request):

        return self.success(
            message="Platform configuration retrieved successfully.",
            data=ConfigurationRepository.all(),
        )


class PlatformJobsAPIView(EnterpriseAPIView):

    def get(self, request):

        return self.success(
            message="Platform jobs retrieved successfully.",
            data={
                "completed_jobs": JobRepository.count(),
            }
        )

class PlatformSchedulerAPIView(EnterpriseAPIView):

    def get(self, request):

        return self.success(
            message="Platform schedules retrieved successfully.",
            data={
                "schedules": ScheduleRepository.count(),
            }
        )