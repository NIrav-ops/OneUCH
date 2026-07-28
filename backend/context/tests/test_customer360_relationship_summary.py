from django.test import TestCase

from inbox.models import Organization

from context.models import (
    BusinessObject,
    BusinessObjectType,
    BusinessRelationship,
)

from context.services.customer360 import (
    Customer360Service,
)


class Customer360RelationshipSummaryTests(TestCase):

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

        self.microsoft = BusinessObject.objects.create(
            organization=organization,
            object_type=object_type,
            name="Microsoft",
            status="active",
        )

        BusinessRelationship.objects.create(
            source_object=self.google,
            target_object=self.microsoft,
            relationship_type="RELATED_TO",
        )

        self.service = Customer360Service()

    def test_relationship_count(self):

        result = self.service.build(
            business_object=self.google,
        )

        self.assertEqual(
            result["relationships"]["count"],
            1,
        )

    def test_relationship_name(self):

        result = self.service.build(
            business_object=self.google,
        )

        self.assertEqual(
            result["relationships"]["relationships"][0]["object"],
            "Microsoft",
        )

    def test_relationship_type(self):

        result = self.service.build(
            business_object=self.google,
        )

        self.assertEqual(
            result["relationships"]["relationships"][0]["relationship"],
            "RELATED_TO",
        )