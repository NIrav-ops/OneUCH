from datetime import datetime, timezone as dt_timezone

from django.contrib.auth import get_user_model
from django.test import TestCase

from actions.models import (
    ExpectedResponseItem,
    FollowUpItem,
)
from inbox.models import (
    Conversation,
    InboxMessage,
    Organization,
)

from knowledge.services.workflow.followup_engine import (
    FollowupEngine,
)


User = get_user_model()


class FollowupEngineTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="followup-engine@example.com",
            password="testpass123",
        )

        self.organization = Organization.objects.create(
            name="Followup Engine Org",
            slug="followup-engine-org",
        )

        self.other_organization = Organization.objects.create(
            name="Other Followup Org",
            slug="other-followup-org",
        )

        self.conversation = Conversation.objects.create(
            user=self.user,
            organization=self.organization,
            subject="Follow-up conversation",
            conversation_key="followup-engine-conversation",
        )

        self.other_conversation = Conversation.objects.create(
            user=self.user,
            organization=self.other_organization,
            subject="Other follow-up conversation",
            conversation_key="other-followup-engine-conversation",
        )

        self.message = InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            platform="gmail",
            direction="inbound",
            external_message_id="followup-engine-message",
            sender="vendor@example.com",
            recipients=self.user.email,
            subject="Vendor update",
            body="Please follow up tomorrow.",
            received_at=datetime(
                2026,
                8,
                27,
                8,
                0,
                tzinfo=dt_timezone.utc,
            ),
        )

        self.other_message = InboxMessage.objects.create(
            user=self.user,
            organization=self.other_organization,
            conversation=self.other_conversation,
            platform="gmail",
            direction="inbound",
            external_message_id="other-followup-engine-message",
            sender="other@example.com",
            recipients=self.user.email,
            subject="Other vendor update",
            body="Vendor will confirm tomorrow.",
            received_at=datetime(
                2026,
                8,
                27,
                9,
                0,
                tzinfo=dt_timezone.utc,
            ),
        )

        self.engine = FollowupEngine()

    def create_followup(
        self,
        *,
        status="pending",
        organization=None,
        conversation=None,
        message=None,
    ):
        if organization is None:
            organization = self.organization

        if conversation is None:
            conversation = self.conversation

        if message is None:
            message = self.message

        return FollowUpItem.objects.create(
            user=self.user,
            organization=organization,
            conversation=conversation,
            last_message=message,
            status=status,
        )

    def create_expected_response(
        self,
        *,
        status="waiting",
        organization=None,
        conversation=None,
        message=None,
    ):
        if organization is None:
            organization = self.organization

        if conversation is None:
            conversation = self.conversation

        if message is None:
            message = self.message

        return ExpectedResponseItem.objects.create(
            user=self.user,
            organization=organization,
            conversation=conversation,
            source_message=message,
            status=status,
        )

    def test_empty_organization_returns_zero_counts(self):
        result = self.engine.build(
            organization=self.organization,
        )

        self.assertEqual(
            result,
            {
                "required": 0,
                "completed": 0,
                "pending": 0,
            },
        )

    def test_mixed_followup_and_expected_response_counts(self):
        self.create_followup(
            status="pending",
        )

        self.create_followup(
            status="completed",
        )

        self.create_followup(
            status="ignored",
        )

        self.create_expected_response(
            status="waiting",
        )

        self.create_expected_response(
            status="received",
        )

        self.create_expected_response(
            status="ignored",
        )

        result = self.engine.build(
            organization=self.organization,
        )

        self.assertEqual(
            result["required"],
            6,
        )

        self.assertEqual(
            result["completed"],
            2,
        )

        self.assertEqual(
            result["pending"],
            2,
        )

    def test_ignored_items_only_count_as_required(self):
        self.create_followup(
            status="ignored",
        )

        self.create_expected_response(
            status="ignored",
        )

        result = self.engine.build(
            organization=self.organization,
        )

        self.assertEqual(
            result,
            {
                "required": 2,
                "completed": 0,
                "pending": 0,
            },
        )

    def test_counts_are_isolated_by_organization(self):
        self.create_followup(
            status="pending",
        )

        self.create_expected_response(
            status="received",
        )

        self.create_followup(
            organization=self.other_organization,
            conversation=self.other_conversation,
            message=self.other_message,
            status="completed",
        )

        self.create_expected_response(
            organization=self.other_organization,
            conversation=self.other_conversation,
            message=self.other_message,
            status="waiting",
        )

        result = self.engine.build(
            organization=self.organization,
        )

        self.assertEqual(
            result,
            {
                "required": 2,
                "completed": 1,
                "pending": 1,
            },
        )
