from datetime import timedelta

from django.utils import timezone

from context.tests.base import EnterpriseBaseTestCase

from inbox.models import InboxMessage

from knowledge.services.response_time_analytics import (
    ResponseTimeAnalyticsService,
)


class ResponseTimeAnalyticsTests(
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
            external_message_id="msg2",
            sender="tester@example.com",
            recipients="john@example.com",
            subject="Reply",
            body="Reply",
            received_at=timezone.now() + timedelta(minutes=10),
        )

        self.service = (
            ResponseTimeAnalyticsService()
        )

    def test_pairs(self):

        result = self.service.build(
            organization=self.organization,
        )

        self.assertEqual(
            result["pairs"],
            1,
        )

    def test_average_positive(self):

        result = self.service.build(
            organization=self.organization,
        )

        self.assertGreater(
            result["average_minutes"],
            0,
        )

    def test_contract(self):

        result = self.service.build(
            organization=self.organization,
        )

        expected = {

            "pairs",
            "average_minutes",
            "max_minutes",
            "min_minutes",

        }

        self.assertEqual(
            set(result.keys()),
            expected,
        )

    def test_max_ge_min(self):

        result = self.service.build(
            organization=self.organization,
        )

        self.assertGreaterEqual(
            result["max_minutes"],
            result["min_minutes"],
        )