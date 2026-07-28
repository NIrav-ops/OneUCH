from django.test import TestCase

from inbox.models import Organization

from context.models import (
    BusinessObject,
    BusinessObjectType,
)

from context.services.customer360 import (
    Customer360Service,
)


class Customer360Tests(TestCase):

    def setUp(self):

        organization = Organization.objects.create(
            name="Test Org",
        )

        object_type = BusinessObjectType.objects.create(
            name="Company",
        )

        self.google = BusinessObject.objects.create(
            organization=organization,
            object_type=object_type,
            name="Google",
            status="active",
        )

        self.service = Customer360Service()

    def test_build(self):

        result = self.service.build(
            business_object=self.google,
        )

        self.assertEqual(
            result["business_object"],
            self.google,
        )

    def test_structure(self):

        result = self.service.build(
            business_object=self.google,
        )

        self.assertIn(
            "graph",
            result,
        )

        self.assertIn(
            "relationships",
            result,
        )

        self.assertIn(
            "knowledge",
            result,
        )

        self.assertIn(
            "timeline",
            result,
        )

        self.assertIn(
            "metrics",
            result,
        )

        self.assertIn(
            "summary",
            result,
        )