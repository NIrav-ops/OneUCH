from django.test import TestCase

from platform_core.api.versioning import (
    CURRENT_VERSION,
)


class VersionTests(TestCase):

    def test_short(self):

        self.assertEqual(

            CURRENT_VERSION.short,

            "v1",

        )

    def test_full(self):

        self.assertEqual(

            CURRENT_VERSION.full,

            "v1.0.0",

        )