from datetime import datetime, timedelta, timezone as dt_timezone

from django.contrib.auth import get_user_model
from django.test import TestCase

from inbox.models import (
    Conversation,
    InboxMessage,
    Organization,
)
from actions.models import ExpectedResponseItem
from actions.expected_response_tasks import (
    analyze_new_expected_responses,
)


User = get_user_model()


class ExpectedResponseAnalysisTaskTests(
    TestCase
):

    def setUp(self):
        self.user = User.objects.create_user(
            email="expected@example.com",
            password="testpass123",
        )

        self.organization = Organization.objects.create(
            name="Expected Response Org",
            slug="expected-response-org",
        )

        self.conversation = Conversation.objects.create(
            user=self.user,
            organization=self.organization,
            subject="Expected response",
            conversation_key="expected-response-worker",
        )

    def create_message(
        self,
        *,
        body,
        direction="inbound",
        is_draft=False,
        analyzed=False,
        sender=None,
        recipients=None,
    ):
        number = (
            InboxMessage.objects.count()
            + 1
        )

        if sender is None:
            sender = (
                "vendor@example.com"
                if direction == "inbound"
                else "expected@example.com"
            )

        if recipients is None:
            recipients = (
                "expected@example.com"
                if direction == "inbound"
                else "vendor@example.com"
            )

        return InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            platform="gmail",
            direction=direction,
            external_message_id=(
                f"expected-msg-{number}"
            ),
            sender=sender,
            recipients=recipients,
            subject="Expected response test",
            body=body,
            received_at=(
                datetime(
                    2026,
                    8,
                    26,
                    8,
                    0,
                    tzinfo=dt_timezone.utc,
                )
                + timedelta(
                    minutes=number
                )
            ),
            is_draft=is_draft,
            expected_response_analyzed=analyzed,
        )

    def test_inbound_future_commitment_creates_item(
        self,
    ):
        msg = self.create_message(
            body=(
                "Vendor will confirm tomorrow."
            )
        )

        processed = (
            analyze_new_expected_responses.run(
                message_ids=[msg.id]
            )
        )

        self.assertEqual(processed, 1)

        msg.refresh_from_db()

        self.assertTrue(
            msg.expected_response_analyzed
        )

        item = ExpectedResponseItem.objects.get(
            source_message=msg
        )

        self.assertEqual(
            item.status,
            "waiting",
        )

        self.assertEqual(
            item.response_due_at.date().isoformat(),
            "2026-08-27",
        )

    def test_outbound_request_for_later_response_creates_item(
        self,
    ):
        msg = self.create_message(
            direction="outbound",
            body=(
                "Please let me know once approved."
            ),
        )

        analyze_new_expected_responses.run(
            message_ids=[msg.id]
        )

        self.assertTrue(
            ExpectedResponseItem.objects.filter(
                source_message=msg
            ).exists()
        )

    def test_outbound_self_commitment_is_not_expected_response(
        self,
    ):
        msg = self.create_message(
            direction="outbound",
            body=(
                "We will send the quotation "
                "tomorrow."
            ),
        )

        analyze_new_expected_responses.run(
            message_ids=[msg.id]
        )

        msg.refresh_from_db()

        self.assertTrue(
            msg.expected_response_analyzed
        )

        self.assertFalse(
            ExpectedResponseItem.objects.filter(
                source_message=msg
            ).exists()
        )

    def test_non_expected_response_marks_analyzed(
        self,
    ):
        msg = self.create_message(
            body="Thanks for the update."
        )

        processed = (
            analyze_new_expected_responses.run(
                message_ids=[msg.id]
            )
        )

        self.assertEqual(processed, 1)

        msg.refresh_from_db()

        self.assertTrue(
            msg.expected_response_analyzed
        )

        self.assertFalse(
            ExpectedResponseItem.objects.filter(
                source_message=msg
            ).exists()
        )

    def test_draft_is_excluded(
        self,
    ):
        msg = self.create_message(
            body=(
                "Please let me know once approved."
            ),
            is_draft=True,
        )

        processed = (
            analyze_new_expected_responses.run(
                message_ids=[msg.id]
            )
        )

        self.assertEqual(processed, 0)

        msg.refresh_from_db()

        self.assertFalse(
            msg.expected_response_analyzed
        )

    def test_message_ids_targeting(
        self,
    ):
        first = self.create_message(
            body="Vendor will confirm tomorrow."
        )

        second = self.create_message(
            body="Customer will confirm Friday."
        )

        processed = (
            analyze_new_expected_responses.run(
                message_ids=[second.id]
            )
        )

        self.assertEqual(processed, 1)

        first.refresh_from_db()
        second.refresh_from_db()

        self.assertFalse(
            first.expected_response_analyzed
        )

        self.assertTrue(
            second.expected_response_analyzed
        )

    def test_reanalysis_does_not_duplicate(
        self,
    ):
        msg = self.create_message(
            body="Vendor will confirm tomorrow."
        )

        analyze_new_expected_responses.run(
            message_ids=[msg.id]
        )

        msg.expected_response_analyzed = False
        msg.save(
            update_fields=[
                "expected_response_analyzed"
            ]
        )

        analyze_new_expected_responses.run(
            message_ids=[msg.id]
        )

        self.assertEqual(
            ExpectedResponseItem.objects.filter(
                source_message=msg
            ).count(),
            1,
        )

    def test_second_commitment_same_conversation_updates_waiting_item(
        self,
    ):
        first = self.create_message(
            body="Vendor will confirm tomorrow."
        )

        analyze_new_expected_responses.run(
            message_ids=[first.id]
        )

        first_item = (
            ExpectedResponseItem.objects.get(
                conversation=self.conversation,
                status="waiting",
            )
        )

        second = self.create_message(
            body="Vendor will confirm by Friday."
        )

        analyze_new_expected_responses.run(
            message_ids=[second.id]
        )

        self.assertEqual(
            ExpectedResponseItem.objects.filter(
                conversation=self.conversation,
                status="waiting",
            ).count(),
            1,
        )

        item = ExpectedResponseItem.objects.get(
            conversation=self.conversation,
            status="waiting",
        )

        self.assertEqual(
            item.id,
            first_item.id,
        )

        self.assertEqual(
            item.source_message_id,
            second.id,
        )

        self.assertEqual(
            item.response_due_at.date().isoformat(),
            "2026-08-28",
        )

    def test_later_inbound_message_resolves_existing_wait(
        self,
    ):
        first = self.create_message(
            body="Vendor will confirm tomorrow."
        )

        analyze_new_expected_responses.run(
            message_ids=[first.id]
        )

        item = ExpectedResponseItem.objects.get(
            conversation=self.conversation,
            status="waiting",
        )

        reply = self.create_message(
            body="Here is the confirmation."
        )

        analyze_new_expected_responses.run(
            message_ids=[reply.id]
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

    def test_received_item_allows_new_waiting_obligation(
        self,
    ):
        first = self.create_message(
            body="Vendor will confirm tomorrow."
        )

        analyze_new_expected_responses.run(
            message_ids=[first.id]
        )

        reply = self.create_message(
            body="Here is the confirmation."
        )

        analyze_new_expected_responses.run(
            message_ids=[reply.id]
        )

        new_commitment = self.create_message(
            body=(
                "Customer will confirm "
                "next Monday."
            )
        )

        analyze_new_expected_responses.run(
            message_ids=[new_commitment.id]
        )

        self.assertEqual(
            ExpectedResponseItem.objects.filter(
                conversation=self.conversation,
            ).count(),
            2,
        )

        self.assertEqual(
            ExpectedResponseItem.objects.filter(
                conversation=self.conversation,
                status="received",
            ).count(),
            1,
        )

        self.assertEqual(
            ExpectedResponseItem.objects.filter(
                conversation=self.conversation,
                status="waiting",
            ).count(),
            1,
        )

    def test_outbound_message_does_not_resolve_existing_wait(
        self,
    ):
        first = self.create_message(
            body="Vendor will confirm tomorrow."
        )

        analyze_new_expected_responses.run(
            message_ids=[first.id]
        )

        item = ExpectedResponseItem.objects.get(
            conversation=self.conversation,
            status="waiting",
        )

        outbound = self.create_message(
            direction="outbound",
            body="Thanks, we will wait.",
        )

        analyze_new_expected_responses.run(
            message_ids=[outbound.id]
        )

        item.refresh_from_db()

        self.assertEqual(
            item.status,
            "waiting",
        )

        self.assertIsNone(
            item.resolved_by_message_id
        )

    def test_quoted_original_commitment_does_not_prevent_resolution(self):
        first = self.create_message(
            body="Vendor will confirm tomorrow.",
        )

        analyze_new_expected_responses.run(
            message_ids=[first.id]
        )

        item = ExpectedResponseItem.objects.get(
            source_message=first
        )

        reply = self.create_message(
            body=(
                "Here is the confirmation.\n\n"
                "On Wed, Aug 26, 2026 at 5:54 PM "
                "sender@example.com wrote:\n"
                "Vendor will confirm tomorrow."
            ),
        )

        analyze_new_expected_responses.run(
            message_ids=[reply.id]
        )

        item.refresh_from_db()

        self.assertEqual(
            item.status,
            "received",
        )
        self.assertEqual(
            item.source_message_id,
            first.id,
        )
        self.assertEqual(
            item.resolved_by_message_id,
            reply.id,
        )
        self.assertEqual(
            item.resolved_at,
            reply.received_at,
        )


    def test_inline_gmail_quote_does_not_prevent_resolution(self):
        first = self.create_message(
            body="Vendor will confirm tomorrow.",
        )

        analyze_new_expected_responses.run(
            message_ids=[first.id]
        )

        item = ExpectedResponseItem.objects.get(
            source_message=first
        )

        reply = self.create_message(
            body=(
                "Here is the confirmation. "
                "On Wed, Aug 26, 2026 at 5:54 PM "
                "sender@example.com wrote: "
                "Vendor will confirm tomorrow."
            ),
        )

        analyze_new_expected_responses.run(
            message_ids=[reply.id]
        )

        item.refresh_from_db()

        self.assertEqual(
            item.status,
            "received",
        )
        self.assertEqual(
            item.source_message_id,
            first.id,
        )
        self.assertEqual(
            item.resolved_by_message_id,
            reply.id,
        )
        self.assertEqual(
            item.resolved_at,
            reply.received_at,
        )

