from datetime import datetime, timedelta, timezone as dt_timezone

from django.contrib.auth import get_user_model
from django.test import TestCase

from inbox.models import (
    Conversation,
    InboxMessage,
    Organization,
)
from actions.models import ExpectedResponseItem
from actions.expected_response_resolution import (
    resolve_expected_responses_for_message,
)


User = get_user_model()


class ExpectedResponseResolutionTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="resolution@example.com",
            password="testpass123",
        )

        self.organization = Organization.objects.create(
            name="Resolution Org",
            slug="resolution-org",
        )

        self.conversation = Conversation.objects.create(
            user=self.user,
            organization=self.organization,
            subject="Vendor confirmation",
            conversation_key="expected-response-resolution",
        )

        self.source_time = datetime(
            2026,
            8,
            26,
            8,
            0,
            tzinfo=dt_timezone.utc,
        )

        self.source_message = InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            platform="gmail",
            direction="inbound",
            external_message_id="resolution-source",
            sender="vendor@example.com",
            recipients="resolution@example.com",
            subject="Vendor confirmation",
            body="Vendor will confirm tomorrow.",
            received_at=self.source_time,
        )

    def create_reply(
        self,
        *,
        sender="vendor@example.com",
        direction="inbound",
        received_at=None,
    ):
        if received_at is None:
            received_at = (
                self.source_time
                + timedelta(hours=4)
            )

        return InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            platform="gmail",
            direction=direction,
            external_message_id=(
                f"resolution-reply-"
                f"{InboxMessage.objects.count() + 1}"
            ),
            sender=sender,
            recipients="resolution@example.com",
            subject="Re: Vendor confirmation",
            body="Here is the confirmation.",
            received_at=received_at,
        )

    def test_matching_sender_resolves_waiting_item(self):
        item = ExpectedResponseItem.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            source_message=self.source_message,
            expected_from="vendor@example.com",
            evidence_text="Vendor will confirm tomorrow.",
            status="waiting",
        )

        reply = self.create_reply()

        resolved = resolve_expected_responses_for_message(
            reply
        )

        self.assertEqual(resolved, 1)

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
            reply.received_at,
        )

    def test_wrong_sender_does_not_resolve_known_expected_from(self):
        item = ExpectedResponseItem.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            source_message=self.source_message,
            expected_from="vendor@example.com",
            status="waiting",
        )

        reply = self.create_reply(
            sender="other@example.com"
        )

        resolved = resolve_expected_responses_for_message(
            reply
        )

        self.assertEqual(resolved, 0)

        item.refresh_from_db()

        self.assertEqual(
            item.status,
            "waiting",
        )

    def test_unknown_expected_from_resolves_on_later_inbound(self):
        item = ExpectedResponseItem.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            source_message=self.source_message,
            expected_from=None,
            status="waiting",
        )

        reply = self.create_reply(
            sender="customer@example.com"
        )

        resolved = resolve_expected_responses_for_message(
            reply
        )

        self.assertEqual(resolved, 1)

        item.refresh_from_db()

        self.assertEqual(
            item.status,
            "received",
        )

    def test_outbound_message_does_not_resolve(self):
        item = ExpectedResponseItem.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            source_message=self.source_message,
            expected_from=None,
            status="waiting",
        )

        outbound = self.create_reply(
            direction="outbound"
        )

        resolved = resolve_expected_responses_for_message(
            outbound
        )

        self.assertEqual(resolved, 0)

        item.refresh_from_db()

        self.assertEqual(
            item.status,
            "waiting",
        )

    def test_older_message_does_not_resolve(self):
        item = ExpectedResponseItem.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            source_message=self.source_message,
            expected_from=None,
            status="waiting",
        )

        older = self.create_reply(
            received_at=(
                self.source_time
                - timedelta(hours=1)
            )
        )

        resolved = resolve_expected_responses_for_message(
            older
        )

        self.assertEqual(resolved, 0)

        item.refresh_from_db()

        self.assertEqual(
            item.status,
            "waiting",
        )

    def test_completed_or_ignored_items_are_not_resolved(self):
        completed = ExpectedResponseItem.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            source_message=self.source_message,
            status="received",
        )

        ignored = ExpectedResponseItem.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            source_message=self.source_message,
            status="ignored",
        )

        reply = self.create_reply()

        resolved = resolve_expected_responses_for_message(
            reply
        )

        self.assertEqual(resolved, 0)

        completed.refresh_from_db()
        ignored.refresh_from_db()

        self.assertEqual(
            completed.status,
            "received",
        )

        self.assertEqual(
            ignored.status,
            "ignored",
        )

    def test_display_name_sender_matches_expected_email(self):
        item = ExpectedResponseItem.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            source_message=self.source_message,
            expected_from="vendor@example.com",
            status="waiting",
        )

        reply = self.create_reply(
            sender="Vendor Team <vendor@example.com>",
        )

        resolved = resolve_expected_responses_for_message(
            reply
        )

        self.assertEqual(
            resolved,
            1,
        )

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
            reply.received_at,
        )

