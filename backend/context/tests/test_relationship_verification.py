from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from inbox.models import Organization

from context.models import (
    BusinessObject,
    BusinessObjectType,
    BusinessRelationship,
)

from context.services.relationship_verification import (
    RelationshipVerificationService,
)


class RelationshipVerificationTests(TestCase):

    def setUp(self):

        self.organization = Organization.objects.create(
            name="Test Org",
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

        self.relationship = BusinessRelationship.objects.create(
            source_object=self.google,
            target_object=self.microsoft,
            relationship_type="RELATED_TO",
            confidence=50,
            evidence_count=2,
        )

    def test_verify_relationship(self):

        RelationshipVerificationService.verify(
            self.relationship
        )

        self.relationship.refresh_from_db()

        self.assertIsNotNone(
            self.relationship.last_verified
        )

    def test_new_relationship_not_stale(self):

        RelationshipVerificationService.verify(
            self.relationship
        )

        self.relationship.refresh_from_db()

        self.assertFalse(

            RelationshipVerificationService.is_stale(
                self.relationship
            )

        )

    def test_old_relationship_stale(self):

        self.relationship.last_verified = (
            timezone.now() -
            timedelta(days=365)
        )

        self.relationship.save()

        self.assertTrue(

            RelationshipVerificationService.is_stale(
                self.relationship
            )

        )

    def test_relationship_without_timestamp(self):

        self.relationship.last_verified = None

        self.relationship.save()

        self.assertTrue(

            RelationshipVerificationService.is_stale(
                self.relationship
            )

        )