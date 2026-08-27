from datetime import datetime, timezone as dt_timezone

from django.contrib.auth import get_user_model
from django.test import TestCase

from inbox.models import (
    Conversation,
    InboxMessage,
    Organization,
)
from actions.models import ExpectedResponseItem


User = get_user_model()


class ExpectedResponseItemModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="waiting@example.com",
            password="testpass123",
        )

        self.organization = Organization.objects.create(
            name="Waiting Response Org",
            slug="waiting-response-org",
        )

        self.conversation = Conversation.objects.create(
            user=self.user,
            organization=self.organization,
            subject="Vendor quotation",
            conversation_key="waiting-response-test",
        )

        self.message = InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            platform="gmail",
            direction="inbound",
            external_message_id="waiting-msg-001",
            sender="vendor@example.com",
            recipients="waiting@example.com",
            subject="Vendor quotation",
            body=(
                "We will send the revised quotation "
                "by Friday."
            ),
            received_at=datetime(
                2026,
                8,
                26,
                8,
                0,
                tzinfo=dt_timezone.utc,
            ),
        )

    def test_waiting_response_can_be_undated(self):
        item = ExpectedResponseItem.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            source_message=self.message,
            expected_from="vendor@example.com",
            evidence_text=(
                "We will send the revised quotation."
            ),
        )

        self.assertEqual(
            item.status,
            "waiting",
        )

        self.assertIsNone(
            item.response_due_at
        )

        self.assertIsNone(
            item.resolved_by_message
        )

        self.assertIsNone(
            item.resolved_at
        )

    def test_waiting_response_can_have_due_date(self):
        due_at = datetime(
            2026,
            8,
            28,
            0,
            0,
            tzinfo=dt_timezone.utc,
        )

        item = ExpectedResponseItem.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            source_message=self.message,
            expected_from="vendor@example.com",
            evidence_text=(
                "We will send the revised quotation "
                "by Friday."
            ),
            response_due_at=due_at,
        )

        self.assertEqual(
            item.response_due_at,
            due_at,
        )

    def test_received_response_can_be_recorded(self):
        item = ExpectedResponseItem.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            source_message=self.message,
            expected_from="vendor@example.com",
            evidence_text=(
                "We will send the revised quotation."
            ),
        )

        reply = InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            platform="gmail",
            direction="inbound",
            external_message_id="waiting-msg-002",
            sender="vendor@example.com",
            recipients="waiting@example.com",
            subject="Re: Vendor quotation",
            body="Please find the revised quotation.",
            received_at=datetime(
                2026,
                8,
                27,
                8,
                0,
                tzinfo=dt_timezone.utc,
            ),
        )

        resolved_at = datetime(
            2026,
            8,
            27,
            8,
            0,
            tzinfo=dt_timezone.utc,
        )

        item.status = "received"
        item.resolved_by_message = reply
        item.resolved_at = resolved_at
        item.save()

        item.refresh_from_db()

        self.assertEqual(
            item.status,
            "received",
        )

        self.assertEqual(
            item.resolved_by_message_id,
            reply.id,
        )

        self.assertEqual(
            item.resolved_at,
            resolved_at,
        )


