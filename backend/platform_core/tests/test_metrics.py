from django.test import TestCase

from platform_core.metrics import (
    PlatformMetrics,
)


class PlatformMetricsTests(TestCase):

    def test_metrics(self):

        result = PlatformMetrics().build()

        self.assertIn(
            "services",
            result,
        )

        self.assertIn(
            "loaded",
            result,
        )