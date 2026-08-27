from datetime import (
    datetime,
    timezone as dt_timezone,
)

from django.contrib.auth import get_user_model
from django.test import TestCase

from inbox.models import (
    Conversation,
    InboxMessage,
    Organization,
)

from actions.models import FollowUpItem
from actions.followup_tasks import (
    analyze_new_followups,
)


User = get_user_model()


class FollowUpAnalysisTaskTests(
    TestCase
):
    def setUp(self):
        self.user = User.objects.create_user(
            email="followup@example.com",
            password="testpass123",
        )

        self.organization = (
            Organization.objects.create(
                name="FollowUp Org",
                slug="followup-org",
            )
        )

        self.conversation = (
            Conversation.objects.create(
                user=self.user,
                organization=self.organization,
                subject="Follow-up conversation",
            )
        )

    def create_message(
        self,
        *,
        body,
        direction="inbound",
        is_draft=False,
        analyzed=False,
    ):
        return InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            platform="gmail",
            external_message_id=(
                f"msg-{InboxMessage.objects.count() + 1}"
            ),
            direction=direction,
            sender="sender@example.com",
            recipients="followup@example.com",
            subject="Follow-up test",
            body=body,
            received_at=datetime(
                2026,
                8,
                26,
                5,
                0,
                tzinfo=dt_timezone.utc,
            ),
            is_draft=is_draft,
            followup_analyzed=analyzed,
        )

    def test_explicit_followup_creates_item(
        self,
    ):
        msg = self.create_message(
            body=(
                "Please follow up with the vendor "
                "tomorrow."
            )
        )

        processed = (
            analyze_new_followups.run(
                message_ids=[msg.id]
            )
        )

        self.assertEqual(
            processed,
            1,
        )

        msg.refresh_from_db()

        self.assertTrue(
            msg.followup_analyzed
        )

        followup = FollowUpItem.objects.get(
            last_message=msg
        )

        self.assertEqual(
            followup.status,
            "pending",
        )

        self.assertEqual(
            followup.followup_due_at.date().isoformat(),
            "2026-08-27",
        )

    def test_undated_followup_creates_item(
        self,
    ):
        msg = self.create_message(
            body=(
                "Please follow up with the vendor."
            )
        )

        analyze_new_followups.run(
            message_ids=[msg.id]
        )

        followup = FollowUpItem.objects.get(
            last_message=msg
        )

        self.assertIsNone(
            followup.followup_due_at
        )

    def test_non_followup_marks_analyzed(
        self,
    ):
        msg = self.create_message(
            body=(
                "Thank you for your reply."
            )
        )

        processed = (
            analyze_new_followups.run(
                message_ids=[msg.id]
            )
        )

        self.assertEqual(
            processed,
            1,
        )

        msg.refresh_from_db()

        self.assertTrue(
            msg.followup_analyzed
        )

        self.assertFalse(
            FollowUpItem.objects.filter(
                last_message=msg
            ).exists()
        )

    def test_outbound_message_is_excluded(
        self,
    ):
        msg = self.create_message(
            body=(
                "Please follow up with the vendor "
                "tomorrow."
            ),
            direction="outbound",
        )

        processed = (
            analyze_new_followups.run(
                message_ids=[msg.id]
            )
        )

        self.assertEqual(
            processed,
            0,
        )

        msg.refresh_from_db()

        self.assertFalse(
            msg.followup_analyzed
        )

        self.assertFalse(
            FollowUpItem.objects.filter(
                last_message=msg
            ).exists()
        )

    def test_draft_message_is_excluded(
        self,
    ):
        msg = self.create_message(
            body=(
                "Please follow up with the vendor "
                "tomorrow."
            ),
            is_draft=True,
        )

        processed = (
            analyze_new_followups.run(
                message_ids=[msg.id]
            )
        )

        self.assertEqual(
            processed,
            0,
        )

        msg.refresh_from_db()

        self.assertFalse(
            msg.followup_analyzed
        )

    def test_message_ids_targeting(
        self,
    ):
        first = self.create_message(
            body=(
                "Please follow up with the vendor "
                "tomorrow."
            )
        )

        second = self.create_message(
            body=(
                "Please follow up with finance "
                "tomorrow."
            )
        )

        processed = (
            analyze_new_followups.run(
                message_ids=[second.id]
            )
        )

        self.assertEqual(
            processed,
            1,
        )

        first.refresh_from_db()
        second.refresh_from_db()

        self.assertFalse(
            first.followup_analyzed
        )

        self.assertTrue(
            second.followup_analyzed
        )

        self.assertFalse(
            FollowUpItem.objects.filter(
                last_message=first
            ).exists()
        )

        self.assertTrue(
            FollowUpItem.objects.filter(
                last_message=second
            ).exists()
        )

    def test_reanalysis_does_not_duplicate(
        self,
    ):
        msg = self.create_message(
            body=(
                "Please follow up with the vendor "
                "tomorrow."
            )
        )

        analyze_new_followups.run(
            message_ids=[msg.id]
        )

        msg.followup_analyzed = False
        msg.save(
            update_fields=[
                "followup_analyzed"
            ]
        )

        analyze_new_followups.run(
            message_ids=[msg.id]
        )

        self.assertEqual(
            FollowUpItem.objects.filter(
                last_message=msg
            ).count(),
            1,
        )

    def test_new_message_same_conversation_updates_pending_followup(
        self,
    ):
        first = self.create_message(
            body=(
                "Please follow up with the vendor "
                "tomorrow."
            )
        )

        analyze_new_followups.run(
            message_ids=[first.id]
        )

        first_followup = (
            FollowUpItem.objects.get(
                conversation=self.conversation,
                status="pending",
            )
        )

        second = self.create_message(
            body=(
                "Please follow up with the vendor "
                "by Friday."
            )
        )

        analyze_new_followups.run(
            message_ids=[second.id]
        )

        self.assertEqual(
            FollowUpItem.objects.filter(
                conversation=self.conversation,
                status="pending",
            ).count(),
            1,
        )

        followup = (
            FollowUpItem.objects.get(
                conversation=self.conversation,
                status="pending",
            )
        )

        self.assertEqual(
            followup.id,
            first_followup.id,
        )

        self.assertEqual(
            followup.last_message_id,
            second.id,
        )

        self.assertEqual(
            followup.followup_due_at.date().isoformat(),
            "2026-08-28",
        )

    def test_completed_followup_allows_new_pending_followup(
        self,
    ):
        first = self.create_message(
            body=(
                "Please follow up with the vendor "
                "tomorrow."
            )
        )

        analyze_new_followups.run(
            message_ids=[first.id]
        )

        old_followup = FollowUpItem.objects.get(
            last_message=first
        )

        old_followup.status = "completed"
        old_followup.save(
            update_fields=["status"]
        )

        second = self.create_message(
            body=(
                "Please follow up with finance "
                "by Friday."
            )
        )

        analyze_new_followups.run(
            message_ids=[second.id]
        )

        self.assertEqual(
            FollowUpItem.objects.filter(
                conversation=self.conversation,
            ).count(),
            2,
        )

        self.assertEqual(
            FollowUpItem.objects.filter(
                conversation=self.conversation,
                status="pending",
            ).count(),
            1,
        )

        self.assertTrue(
            FollowUpItem.objects.filter(
                last_message=second,
                status="pending",
            ).exists()
        )

    def test_ignored_followup_allows_new_pending_followup(
        self,
    ):
        first = self.create_message(
            body=(
                "Please follow up with the vendor "
                "tomorrow."
            )
        )

        analyze_new_followups.run(
            message_ids=[first.id]
        )

        old_followup = FollowUpItem.objects.get(
            last_message=first
        )

        old_followup.status = "ignored"
        old_followup.save(
            update_fields=["status"]
        )

        second = self.create_message(
            body=(
                "Let's reconnect next Monday."
            )
        )

        analyze_new_followups.run(
            message_ids=[second.id]
        )

        self.assertEqual(
            FollowUpItem.objects.filter(
                conversation=self.conversation,
                status="pending",
            ).count(),
            1,
        )

        self.assertTrue(
            FollowUpItem.objects.filter(
                last_message=second,
                status="pending",
            ).exists()
        )

