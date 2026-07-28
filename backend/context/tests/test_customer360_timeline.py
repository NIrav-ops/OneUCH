from django.test import TestCase

from inbox.models import Organization

from context.models import (
    BusinessObject,
    BusinessObjectType,
)

from context.services.customer360 import (
    Customer360Service,
)

from knowledge.models import (
    KnowledgeEvidence,
)

from django.contrib.auth import get_user_model

from inbox.models import (
    Conversation,
    InboxMessage,
)

from django.utils import timezone


class Customer360TimelineTests(TestCase):

    def setUp(self):

        organization = Organization.objects.create(
            name="Test Org",
        )

        object_type = BusinessObjectType.objects.create(
            name="Company",
        )

        User = get_user_model()

        self.user = User.objects.create_user(
            email="tester@example.com",
            password="Password123",
        )

        self.company = BusinessObject.objects.create(
            organization=organization,
            object_type=object_type,
            name="Google",
            status="active",
        )

        self.conversation = Conversation.objects.create(
            user=self.user,
            organization=organization,
            subject="Test Conversation",
            conversation_key="timeline_test",
        )

        self.message = InboxMessage.objects.create(
            user=self.user,
            organization=organization,
            conversation=self.conversation,
            platform="gmail",
            direction="inbound",
            external_message_id="msg1",
            sender="test@example.com",
            recipients="tester@example.com",
            subject="Welcome Email",
            body="Initial customer contact",
            received_at=timezone.now(),
        )

        KnowledgeEvidence.objects.create(
            organization=organization,
            business_object=self.company,
            conversation=self.conversation,
            message=self.message,
            evidence_type="EMAIL",
            title="Welcome Email",
            summary="Initial customer contact",
            confidence=100,
            source_channel="gmail",
        )

        self.service = Customer360Service()

    def test_timeline_exists(self):

        result = self.service.build(
            business_object=self.company,
        )

        self.assertEqual(
            len(result["timeline"]),
            1,
        )

    def test_timeline_title(self):

        result = self.service.build(
            business_object=self.company,
        )

        self.assertEqual(
            result["timeline"][0]["title"],
            "Welcome Email",
        )