from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from inbox.models import (
    Organization,
    Conversation,
    InboxMessage,
)

from context.models import (
    BusinessObject,
    BusinessObjectType,
    BusinessRelationship,
)

from knowledge.models import (
    KnowledgeEvidence,
    KnowledgeFact,
)

from knowledge.services.organization_activity import (
    OrganizationActivityService,
)


class OrganizationActivityTests(TestCase):

    def setUp(self):

        User = get_user_model()

        self.user = User.objects.create_user(
            email="tester@example.com",
            password="Password123",
        )

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

        BusinessRelationship.objects.create(
            source_object=self.google,
            target_object=self.microsoft,
        )

        self.conversation = Conversation.objects.create(
            user=self.user,
            organization=self.organization,
            subject="Organization Activity",
            conversation_key="organization_activity",
        )

        self.message = InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            platform="gmail",
            direction="inbound",
            external_message_id="msg1",
            sender="test@example.com",
            recipients="tester@example.com",
            subject="Enterprise",
            body="Testing",
            received_at=timezone.now(),
        )

        self.evidence = KnowledgeEvidence.objects.create(
            organization=self.organization,
            business_object=self.google,
            conversation=self.conversation,
            message=self.message,
            evidence_type="EMAIL",
            title="Enterprise",
            summary="Testing",
            confidence=95,
            source_channel="gmail",
        )

        KnowledgeFact.objects.create(
            organization=self.organization,
            business_object=self.google,
            primary_evidence=self.evidence,
            fact_key="STATUS",
            fact_value="Active",
            confidence=95,
            source_channel="gmail",
        )

        self.service = OrganizationActivityService()

    def test_activity_exists(self):

        result = self.service.build(
            organization=self.organization,
        )

        self.assertEqual(
            len(result),
            2,
        )

    def test_contains_evidence(self):

        result = self.service.build(
            organization=self.organization,
        )

        types = [item["type"] for item in result]

        self.assertIn(
            "EVIDENCE",
            types,
        )

    def test_contains_fact(self):

        result = self.service.build(
            organization=self.organization,
        )

        types = [item["type"] for item in result]

        self.assertIn(
            "FACT",
            types,
        )

    def test_ordering(self):

        result = self.service.build(
            organization=self.organization,
        )

        self.assertGreaterEqual(
            result[0]["timestamp"],
            result[1]["timestamp"],
        )