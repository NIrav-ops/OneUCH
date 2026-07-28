from django.test import TestCase

from inbox.models import Organization
from context.models import (
    BusinessObject,
    BusinessObjectType,
)
from context.services.relationship_repository import (
    RelationshipRepository,
)


class RelationshipRepositoryTests(TestCase):

    def setUp(self):

        self.organization = Organization.objects.create(
            name="Test Organization",
        )

        self.object_type = BusinessObjectType.objects.create(
            name="Company",
        )

        self.google = BusinessObject.objects.create(
            organization=self.organization,
            object_type=self.object_type,
            name="Google",
            status="active",
        )

        self.microsoft = BusinessObject.objects.create(
            organization=self.organization,
            object_type=self.object_type,
            name="Microsoft",
            status="active",
        )

        self.repository = RelationshipRepository()

    def test_create_relationship(self):

        relationship, created = (
            self.repository.get_or_create_relationship(
                source_object=self.google,
                target_object=self.microsoft,
            )
        )

        self.assertTrue(created)

        self.assertEqual(
            relationship.evidence_count,
            1,
        )

    def test_duplicate_relationship(self):

        self.repository.get_or_create_relationship(
            source_object=self.google,
            target_object=self.microsoft,
        )

        relationship, created = (
            self.repository.get_or_create_relationship(
                source_object=self.google,
                target_object=self.microsoft,
            )
        )

        self.assertFalse(created)

        self.assertEqual(
            relationship.evidence_count,
            2,
        )

    def test_relationship_exists(self):

        self.repository.get_or_create_relationship(
            source_object=self.google,
            target_object=self.microsoft,
        )

        self.assertTrue(

            self.repository.relationship_exists(
                self.google,
                self.microsoft,
            )

        )