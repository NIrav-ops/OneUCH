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
)

from knowledge.models import (
    KnowledgeEvidence,
    KnowledgeFact,
)

from context.services.customer360 import (
    Customer360Service,
)
from context.models import BusinessRelationship

# Reuse the same setUp() pattern as the previous Customer360 tests.

class Customer360HealthScoreTests(TestCase):

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

        self.company = BusinessObject.objects.create(
            organization=self.organization,
            object_type=self.object_type,
            name="Google",
            status="active",
        )

        self.partner = BusinessObject.objects.create(
            organization=self.organization,
            object_type=self.object_type,
            name="Microsoft",
            status="active",
        )

        BusinessRelationship.objects.create(
            source_object=self.company,
            target_object=self.partner,
            relationship_type="RELATED_TO",
        )

        self.conversation = Conversation.objects.create(
            user=self.user,
            organization=self.organization,
            subject="Activity Feed",
            conversation_key="activity_feed_test",
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
            subject="Enterprise Agreement",
            body="Renewal discussion",
            received_at=timezone.now(),
        )

        self.evidence = KnowledgeEvidence.objects.create(
            organization=self.organization,
            business_object=self.company,
            conversation=self.conversation,
            message=self.message,
            evidence_type="EMAIL",
            title="Enterprise Agreement",
            summary="Renewal discussion",
            confidence=95,
            source_channel="gmail",
        )

        KnowledgeFact.objects.create(
            organization=self.organization,
            business_object=self.company,
            primary_evidence=self.evidence,
            fact_key="CUSTOMER_STATUS",
            fact_value="Active",
            confidence=95,
            source_channel="gmail",
        )

        self.service = Customer360Service()

    def test_health_exists(self):

        result = self.service.build(
            business_object=self.company,
        )

        self.assertIn(
            "score",
            result["health"],
        )

    def test_status(self):

        result = self.service.build(
            business_object=self.company,
        )

        self.assertEqual(
            result["health"]["status"],
            "Healthy",
        )

    def test_score_positive(self):

        result = self.service.build(
            business_object=self.company,
        )

        self.assertGreater(
            result["health"]["score"],
            0,
        )