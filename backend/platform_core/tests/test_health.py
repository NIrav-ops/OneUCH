from django.test import TestCase

from platform_core.health import (
    PlatformHealth,
)


class PlatformHealthTests(TestCase):

    def test_health(self):

        result = PlatformHealth().build()

        self.assertEqual(
            result["status"],
            "healthy",
        )