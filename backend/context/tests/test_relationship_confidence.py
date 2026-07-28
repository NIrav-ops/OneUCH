from django.test import TestCase

from inbox.models import Organization

from context.models import (
    BusinessObject,
    BusinessObjectType,
    BusinessRelationship,
)

from context.services.relationship_confidence import (
    RelationshipConfidenceEngine,
)


class RelationshipConfidenceTests(TestCase):

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

        self.relationship = BusinessRelationship.objects.create(

            source_object=self.google,

            target_object=self.microsoft,

            relationship_type="RELATED_TO",

            confidence=25,

            evidence_count=1,
        )

    def test_calculate_email_score(self):

        score = RelationshipConfidenceEngine.calculate(

            relationship=self.relationship,

            evidence_type="EMAIL",

        )

        self.assertGreaterEqual(score, 3)

    def test_calculate_payment_score(self):

        score = RelationshipConfidenceEngine.calculate(

            relationship=self.relationship,

            evidence_type="PAYMENT",

        )

        self.assertGreater(score, 10)

    def test_update_confidence(self):

        RelationshipConfidenceEngine.update(

            relationship=self.relationship,

            evidence_type="PAYMENT",

        )

        self.relationship.refresh_from_db()

        self.assertIsNotNone(

            self.relationship.last_verified

        )

    def test_unknown_evidence_type(self):

        score = RelationshipConfidenceEngine.calculate(

            relationship=self.relationship,

            evidence_type="UNKNOWN",

        )

        self.assertGreaterEqual(score, 2)