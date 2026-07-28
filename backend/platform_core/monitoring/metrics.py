from platform_core.registry import (
    ServiceRegistry,
)

from platform_core.jobs.queue import (
    JobQueue,
)

from platform_core.jobs.repository import (
    JobRepository,
)

from platform_core.notifications.repository import (
    NotificationRepository,
)

from platform_core.audit.repository import (
    AuditRepository,
)


class PlatformMetrics:

    def collect(self):

        return {

            "services": len(
                ServiceRegistry._services
            ),

            "queued_jobs": JobQueue.size(),

            "completed_jobs": JobRepository.count(),

            "notifications": NotificationRepository.count(),

            "audit_events": AuditRepository.count(),

        }