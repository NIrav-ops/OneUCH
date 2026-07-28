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

from knowledge.models import KnowledgeEvidence

from context.services.customer360 import Customer360Service


class Customer360MetricsTests(TestCase):

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
            subject="Test",
            conversation_key="metrics_test",
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
            subject="Welcome",
            body="Hello",
            received_at=timezone.now(),
        )

        KnowledgeEvidence.objects.create(
            organization=self.organization,
            business_object=self.company,
            conversation=self.conversation,
            message=self.message,
            evidence_type="EMAIL",
            title="Welcome",
            summary="Email",
            confidence=100,
            source_channel="gmail",
        )

        self.service = Customer360Service()

    def test_metrics_exist(self):

        result = self.service.build(
            business_object=self.company,
        )

        self.assertEqual(
            result["metrics"]["total_evidence"],
            1,
        )

    def test_email_count(self):

        result = self.service.build(
            business_object=self.company,
        )

        self.assertEqual(
            result["metrics"]["emails"],
            1,
        )

    def test_last_activity_exists(self):

        result = self.service.build(
            business_object=self.company,
        )

        self.assertIsNotNone(
            result["metrics"]["last_activity"],
        )