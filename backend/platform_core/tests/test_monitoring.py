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