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

from knowledge.services.organization_metrics import (
    OrganizationMetricsService,
)


class OrganizationMetricsTests(TestCase):

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
            subject="Organization Metrics",
            conversation_key="organization_metrics",
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

        self.service = OrganizationMetricsService()

    def test_business_object_count(self):

        result = self.service.build(
            organization=self.organization,
        )

        self.assertEqual(
            result["business_objects"],
            2,
        )

    def test_relationship_count(self):

        result = self.service.build(
            organization=self.organization,
        )

        self.assertEqual(
            result["relationships"],
            1,
        )

    def test_knowledge_fact_count(self):

        result = self.service.build(
            organization=self.organization,
        )

        self.assertEqual(
            result["knowledge_facts"],
            1,
        )

    def test_knowledge_evidence_count(self):

        result = self.service.build(
            organization=self.organization,
        )

        self.assertEqual(
            result["knowledge_evidence"],
            1,
        )