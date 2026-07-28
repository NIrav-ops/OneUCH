from django.test import TestCase

from platform_core.registry import (
    ServiceRegistry,
)


class RegistryTests(TestCase):

    def tearDown(self):

        ServiceRegistry.clear()

    def test_register(self):

        ServiceRegistry.register(
            "demo",
            object(),
        )

        self.assertTrue(
            ServiceRegistry.exists(
                "demo",
            )
        )

    def test_get(self):

        service = object()

        ServiceRegistry.register(
            "demo",
            service,
        )

        self.assertEqual(
            ServiceRegistry.get(
                "demo",
            ),
            service,
        )

    def test_count(self):

        ServiceRegistry.register(
            "one",
            object(),
        )

        ServiceRegistry.register(
            "two",
            object(),
        )

        self.assertEqual(
            ServiceRegistry.count(),
            2,
        )

    def test_clear(self):

        ServiceRegistry.register(
            "demo",
            object(),
        )

        ServiceRegistry.clear()

        self.assertEqual(
            ServiceRegistry.count(),
            0,
        )