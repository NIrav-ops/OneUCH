from datetime import timedelta

from django.utils import timezone

from inbox.models import InboxMessage

from context.tests.base import EnterpriseBaseTestCase

from knowledge.services.communication_intelligence import (
    CommunicationIntelligenceService,
)


class CommunicationIntelligenceTests(
    EnterpriseBaseTestCase,
):

    def setUp(self):

        super().setUp()

        InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            platform="gmail",
            direction="outbound",
            external_message_id="reply1",
            sender="tester@example.com",
            recipients="john@example.com",
            subject="Reply",
            body="Reply",
            received_at=timezone.now() + timedelta(minutes=10),
        )

        self.service = (
            CommunicationIntelligenceService()
        )

    def test_analytics_exists(self):

        result = self.service.build(
            organization=self.organization,
        )

        self.assertIn(
            "analytics",
            result,
        )

    def test_channels_exists(self):

        result = self.service.build(
            organization=self.organization,
        )

        self.assertIn(
            "channels",
            result,
        )

    def test_trends_exists(self):

        result = self.service.build(
            organization=self.organization,
        )

        self.assertIn(
            "trends",
            result,
        )

    def test_response_times_exists(self):

        result = self.service.build(
            organization=self.organization,
        )

        self.assertIn(
            "response_times",
            result,
        )

    def test_health_exists(self):

        result = self.service.build(
            organization=self.organization,
        )

        self.assertIn(
            "health",
            result,
        )

    def test_contract(self):

        result = self.service.build(
            organization=self.organization,
        )

        expected = {

            "analytics",
            "channels",
            "trends",
            "response_times",
            "health",

        }

        self.assertEqual(
            set(result.keys()),
            expected,
        )