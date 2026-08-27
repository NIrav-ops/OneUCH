from unittest.mock import patch

from django.test import TestCase

from platform_core.monitoring.monitor import (
    PlatformMonitor,
)

from platform_core.monitoring.repository import (
    HealthRepository,
)


class PlatformHealthTests(TestCase):

    def tearDown(self):

        HealthRepository.clear()

    @patch(
        "platform_core.monitoring.monitor."
        "settings.REDIS_CLIENT"
    )
    def test_healthy_dependencies(
        self,
        redis_client,
    ):

        redis_client.ping.return_value = True

        result = PlatformMonitor().check()

        health = HealthRepository.all()[-1]

        self.assertEqual(
            health.status,
            "Healthy",
        )

        self.assertEqual(
            result["dependencies"]["database"]["status"],
            "Healthy",
        )

        self.assertEqual(
            result["dependencies"]["redis"]["status"],
            "Healthy",
        )

    @patch(
        "platform_core.monitoring.monitor."
        "settings.REDIS_CLIENT"
    )
    def test_redis_failure_marks_platform_degraded(
        self,
        redis_client,
    ):

        redis_client.ping.side_effect = (
            ConnectionError(
                "Redis unavailable"
            )
        )

        result = PlatformMonitor().check()

        health = HealthRepository.all()[-1]

        self.assertEqual(
            health.status,
            "Degraded",
        )

        self.assertEqual(
            result["dependencies"]["redis"]["status"],
            "Unhealthy",
        )

        self.assertEqual(
            result["dependencies"]["redis"]["error"],
            "ConnectionError",
        )

    @patch(
        "platform_core.monitoring.monitor.connection"
    )
    @patch(
        "platform_core.monitoring.monitor."
        "settings.REDIS_CLIENT"
    )
    def test_database_failure_marks_platform_degraded(
        self,
        redis_client,
        database_connection,
    ):

        redis_client.ping.return_value = True

        database_connection.ensure_connection.side_effect = (
            RuntimeError(
                "Database unavailable"
            )
        )

        result = PlatformMonitor().check()

        health = HealthRepository.all()[-1]

        self.assertEqual(
            health.status,
            "Degraded",
        )

        self.assertEqual(
            result["dependencies"]["database"]["status"],
            "Unhealthy",
        )

        self.assertEqual(
            result["dependencies"]["database"]["error"],
            "RuntimeError",
        )
