from django.contrib.auth import get_user_model
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APITestCase

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


class Customer360APITests(APITestCase):

    def setUp(self):

        User = get_user_model()

        self.user = User.objects.create_user(
            email="tester@example.com",
            password="Password123",
        )

        self.client.force_authenticate(
            user=self.user,
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
        )

        self.conversation = Conversation.objects.create(
            user=self.user,
            organization=self.organization,
            subject="Customer360",
            conversation_key="customer360_api_test",
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
            body="Renewal",
            received_at=timezone.now(),
        )

        self.evidence = KnowledgeEvidence.objects.create(
            organization=self.organization,
            business_object=self.company,
            conversation=self.conversation,
            message=self.message,
            evidence_type="EMAIL",
            title="Enterprise Agreement",
            summary="Renewal",
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

    def test_customer360_status_code(self):

        response = self.client.get(
            f"/api/context/customer360/{self.company.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_customer360_summary_exists(self):

        response = self.client.get(
            f"/api/context/customer360/{self.company.id}/"
        )

        self.assertIn(
            "summary",
            response.data,
        )

    def test_customer360_health_exists(self):

        response = self.client.get(
            f"/api/context/customer360/{self.company.id}/"
        )

        self.assertIn(
            "health",
            response.data,
        )

    def test_customer360_activity_exists(self):

        response = self.client.get(
            f"/api/context/customer360/{self.company.id}/"
        )

        self.assertIn(
            "activity",
            response.data,
        )

    def test_customer360_relationships_exists(self):

        response = self.client.get(
            f"/api/context/customer360/{self.company.id}/"
        )

        self.assertIn(
            "relationships",
            response.data,
        )

    def test_customer360_requires_authentication(self):

        self.client.logout()

        response = self.client.get(
            f"/api/context/customer360/{self.company.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_invalid_business_object(self):

        response = self.client.get(
            "/api/context/customer360/999999/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_customer360_contract(self):

        response = self.client.get(
            f"/api/context/customer360/{self.company.id}/"
        )

        expected = {
            "business_object",
            "graph",
            "relationships",
            "knowledge",
            "timeline",
            "activity",
            "metrics",
            "summary",
            "health",
        }

        self.assertEqual(
            set(response.data.keys()),
            expected,
        )