from django.test import TestCase

from platform_core.monitoring.monitor import (
    PlatformMonitor,
)

from platform_core.monitoring.repository import (
    HealthRepository,
)


class MonitoringTests(TestCase):

    def tearDown(self):

        HealthRepository.clear()

    def test_monitor(self):

        PlatformMonitor().check()

        self.assertEqual(

            HealthRepository.count(),

            1,

        )

    def test_status(self):

        PlatformMonitor().check()

        status = HealthRepository.all()[0]

        self.assertEqual(

            status.status,

            "Healthy",

        )

    def test_service(self):

        PlatformMonitor().check()

        status = HealthRepository.all()[0]

        self.assertEqual(

            status.service,

            "Platform",

        )

    def test_metrics(self):

        metrics = PlatformMonitor().check()

        self.assertIn(

            "services",

            metrics,

        )

    def test_health_repository_is_bounded(self):

        from platform_core.monitoring.health import (
            HealthStatus,
        )

        for index in range(
            HealthRepository.MAX_ENTRIES + 25
        ):

            HealthRepository.save(
                HealthStatus(
                    service=f"Service-{index}",
                    status="Healthy",
                    details={},
                )
            )

        self.assertEqual(
            HealthRepository.count(),
            HealthRepository.MAX_ENTRIES,
        )

        self.assertEqual(
            HealthRepository.latest().service,
            (
                "Service-"
                f"{HealthRepository.MAX_ENTRIES + 24}"
            ),
        )


    def test_health_status_timestamp_is_created_per_instance(
        self,
    ):

        from django.utils import timezone

        from platform_core.monitoring.health import (
            HealthStatus,
        )

        before = timezone.now()

        first = HealthStatus(
            service="Platform",
            status="Healthy",
            details={},
        )

        second = HealthStatus(
            service="Platform",
            status="Healthy",
            details={},
        )

        after = timezone.now()

        self.assertIsNot(
            first.checked_at,
            second.checked_at,
        )

        self.assertTrue(
            timezone.is_aware(
                first.checked_at
            )
        )

        self.assertTrue(
            timezone.is_aware(
                second.checked_at
            )
        )

        self.assertGreaterEqual(
            first.checked_at,
            before,
        )

        self.assertLessEqual(
            first.checked_at,
            after,
        )

        self.assertGreaterEqual(
            second.checked_at,
            before,
        )

        self.assertLessEqual(
            second.checked_at,
            after,
        )


    def test_metrics_use_public_service_registry_contract(
        self,
    ):

        from unittest.mock import patch

        from platform_core.monitoring.metrics import (
            PlatformMetrics,
        )

        with patch(
            "platform_core.monitoring.metrics."
            "ServiceRegistry.count",
            return_value=7,
        ) as registry_count:

            metrics = (
                PlatformMetrics()
                .collect()
            )

        registry_count.assert_called_once_with()

        self.assertEqual(
            metrics["services"],
            7,
        )
