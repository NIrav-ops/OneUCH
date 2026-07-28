from django.test import TestCase

from platform_core.api.ordering import (
    EnterpriseOrdering,
)


class OrderingTests(TestCase):

    def test_parameter(self):

        self.assertEqual(

            EnterpriseOrdering.parameter,

            "ordering",

        )

    def test_default_fields(self):

        self.assertEqual(

            EnterpriseOrdering.ordering_fields,

            [],

        )

    def test_default_ordering(self):

        self.assertEqual(

            EnterpriseOrdering.default_ordering,

            [],

        )

    def test_backend_exists(self):

        self.assertTrue(

            issubclass(

                EnterpriseOrdering,

                object,

            )

        )

    def test_multiple_fields_supported(self):

        backend = EnterpriseOrdering()

        self.assertEqual(

            backend.parameter,

            "ordering",

        )