from django.test import TestCase

from inbox.models import Organization
from context.models import (
    BusinessObject,
    BusinessObjectType,
)
from context.services.relationship_repository import (
    RelationshipRepository,
)

from context.services.relationship_discovery import (
    RelationshipDiscoveryService,
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

        self.discovery = (
            RelationshipDiscoveryService()
        )

        self.amazon = (
            BusinessObject.objects.create(
                organization=self.organization,
                object_type=self.object_type,
                name="Amazon",
                status="active",
            )
        )

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

    def test_discovery_existing_relationship_strengthens_once(
        self,
    ):

        relationship, created = (
            self.repository
            .get_or_create_relationship(
                source_object=self.google,
                target_object=self.microsoft,
            )
        )

        self.assertTrue(
            created
        )

        self.assertEqual(
            relationship.evidence_count,
            1,
        )

        discovered = (
            self.discovery.discover(
                source_object=self.google,
                related_objects=[
                    self.microsoft,
                ],
            )
        )

        self.assertEqual(
            len(discovered),
            1,
        )

        relationship.refresh_from_db()

        self.assertEqual(
            relationship.evidence_count,
            2,
        )


    def test_candidate_discovery_returns_each_pair_once(
        self,
    ):

        first = (
            self.discovery
            .discover_between_candidates(
                business_objects=[
                    self.google,
                    self.microsoft,
                    self.amazon,
                ],
            )
        )

        self.assertEqual(
            len(first),
            3,
        )

        from context.models import (
            BusinessRelationship,
        )

        self.assertEqual(
            BusinessRelationship.objects.count(),
            3,
        )

        self.assertTrue(
            all(
                relationship.evidence_count
                ==
                1
                for relationship
                in BusinessRelationship.objects.all()
            )
        )

        second = (
            self.discovery
            .discover_between_candidates(
                business_objects=[
                    self.google,
                    self.microsoft,
                    self.amazon,
                ],
            )
        )

        self.assertEqual(
            len(second),
            3,
        )

        self.assertEqual(
            BusinessRelationship.objects.count(),
            3,
        )

        self.assertTrue(
            all(
                relationship.evidence_count
                ==
                2
                for relationship
                in BusinessRelationship.objects.all()
            )
        )
