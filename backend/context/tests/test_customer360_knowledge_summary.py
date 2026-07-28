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


class Customer360KnowledgeSummaryTests(TestCase):

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

        self.conversation = Conversation.objects.create(
            user=self.user,
            organization=self.organization,
            subject="Knowledge",
            conversation_key="knowledge_summary_test",
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

    def test_fact_count(self):

        result = self.service.build(
            business_object=self.company,
        )

        self.assertEqual(
            result["knowledge"]["fact_count"],
            1,
        )

    def test_evidence_count(self):

        result = self.service.build(
            business_object=self.company,
        )

        self.assertEqual(
            result["knowledge"]["evidence_count"],
            1,
        )

    def test_latest_fact(self):

        result = self.service.build(
            business_object=self.company,
        )

        self.assertEqual(
            result["knowledge"]["latest_fact"],
            "Active",
        )