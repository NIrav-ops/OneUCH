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


class EnterpriseBaseTestCase(TestCase):
    """
    Shared enterprise test fixture.

    Every future Context/Knowledge/Graph/Customer360/
    Organization360 test should inherit from this.
    """

    def setUp(self):

        super().setUp()

        User = get_user_model()

        self.user = User.objects.create_user(
            email="tester@example.com",
            password="Password123",
        )

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

        BusinessRelationship.objects.create(
            source_object=self.google,
            target_object=self.microsoft,
        )

        self.conversation = Conversation.objects.create(
            user=self.user,
            organization=self.organization,
            subject="Enterprise Test",
            conversation_key="enterprise_test",
        )

        self.message = InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            platform="gmail",
            direction="inbound",
            external_message_id="msg1",
            sender="sender@example.com",
            recipients="tester@example.com",
            subject="Enterprise Test",
            body="Enterprise Test",
            received_at=timezone.now(),
        )

        self.evidence = KnowledgeEvidence.objects.create(
            organization=self.organization,
            business_object=self.google,
            conversation=self.conversation,
            message=self.message,
            evidence_type="EMAIL",
            title="Enterprise Test",
            summary="Enterprise Test",
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