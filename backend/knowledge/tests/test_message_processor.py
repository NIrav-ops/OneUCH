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
    BusinessIdentity,
    KnowledgeEvidence,
    KnowledgeFact,
)

from knowledge.services.message_processor import (
    MessageProcessor,
)

User = get_user_model()


class MessageProcessorTests(TestCase):

    def setUp(self):

        # --------------------------------------------------
        # User
        # --------------------------------------------------

        self.user = User.objects.create_user(
            email="tester@example.com",
            password="Password123",
        )

        # --------------------------------------------------
        # Organization
        # --------------------------------------------------

        self.organization = Organization.objects.create(
            name="Test Organization",
        )

        # --------------------------------------------------
        # Business Object Type
        # --------------------------------------------------

        self.object_type = BusinessObjectType.objects.create(
            name="Company",
        )

        # --------------------------------------------------
        # Business Object
        # --------------------------------------------------

        self.business_object = BusinessObject.objects.create(
            organization=self.organization,
            object_type=self.object_type,
            name="Google",
            status="active",
        )

        # --------------------------------------------------
        # Identity
        # --------------------------------------------------

        BusinessIdentity.objects.create(
            business_object=self.business_object,
            identity_type="EMAIL",
            value="support@google.com",
            normalized_value="support@google.com",
            source="manual",
        )

        # --------------------------------------------------
        # Conversation
        # --------------------------------------------------

        self.conversation = Conversation.objects.create(
            user=self.user,
            organization=self.organization,
            conversation_key="test_thread",
            subject="Testing",
        )

        # --------------------------------------------------
        # Inbox Message
        # --------------------------------------------------

        self.message = InboxMessage.objects.create(

            user=self.user,

            organization=self.organization,

            conversation=self.conversation,

            platform="gmail",

            direction="inbound",

            external_message_id="MSG001",

            sender="support@google.com",

            recipients="tester@example.com",

            subject="Invoice",

            body="Invoice Received",

            received_at=timezone.now(),

        )

        self.processor = MessageProcessor()

    def test_message_processed(self):

        result = self.processor.process_message(

            organization=self.organization,

            message=self.message,

            sender=self.message.sender,

            subject=self.message.subject,

            body=self.message.body,

            source_channel="gmail",

        )

        self.assertTrue(result["matched"])

        self.assertEqual(
            KnowledgeEvidence.objects.count(),
            1,
        )

        self.assertEqual(
            KnowledgeFact.objects.count(),
            1,
        )

    def test_unknown_sender(self):

        result = self.processor.process_message(

            organization=self.organization,

            message=self.message,

            sender="unknown@test.com",

            subject="Hello",

            body="Random",

            source_channel="gmail",

        )

        self.assertFalse(result["matched"])

    def test_return_structure(self):

        result = self.processor.process_message(

            organization=self.organization,

            message=self.message,

            sender=self.message.sender,

            subject=self.message.subject,

            body=self.message.body,

            source_channel="gmail",

        )

        self.assertIn("matched", result)

        self.assertIn("business_object", result)

        self.assertIn("evidence", result)

        self.assertIn("fact", result)

    def test_multi_candidate_inbound_creates_each_relationship_once(
        self,
    ):

        secondary = (
            BusinessObject.objects.create(
                organization=self.organization,
                object_type=self.object_type,
                name="Google Domain Candidate",
                status="active",
            )
        )

        BusinessIdentity.objects.create(
            business_object=secondary,
            identity_type="DOMAIN",
            value="google.com",
            normalized_value="google.com",
            source="manual",
        )

        result = (
            self.processor.process_message(
                organization=self.organization,
                message=self.message,
                sender=self.message.sender,
                subject=self.message.subject,
                body=self.message.body,
                source_channel="gmail",
            )
        )

        self.assertTrue(
            result["matched"]
        )

        self.assertEqual(
            len(
                result["relationships"]
            ),
            1,
        )

        self.assertEqual(
            BusinessRelationship.objects.count(),
            1,
        )

        relationship = (
            BusinessRelationship.objects.get()
        )

        self.assertEqual(
            relationship.source_object,
            self.business_object,
        )

        self.assertEqual(
            relationship.target_object,
            secondary,
        )

        self.assertEqual(
            relationship.evidence_count,
            1,
        )
