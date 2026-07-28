from context.tests.base import EnterpriseBaseTestCase

from knowledge.services.channel_analytics import (
    ChannelAnalyticsService,
)


class ChannelAnalyticsTests(
    EnterpriseBaseTestCase,
):

    def setUp(self):

        super().setUp()

        self.service = (
            ChannelAnalyticsService()
        )

    def test_total_messages(self):

        result = self.service.build(
            organization=self.organization,
        )

        self.assertEqual(
            result["total_messages"],
            1,
        )

    def test_channel_count(self):

        result = self.service.build(
            organization=self.organization,
        )

        self.assertEqual(
            len(result["channels"]),
            4,
        )

    def test_gmail_percentage(self):

        result = self.service.build(
            organization=self.organization,
        )

        gmail = next(
            c
            for c in result["channels"]
            if c["channel"] == "gmail"
        )

        self.assertEqual(
            gmail["percentage"],
            100.0,
        )

    def test_contract(self):

        result = self.service.build(
            organization=self.organization,
        )

        self.assertIn(
            "channels",
            result,
        )

        self.assertIn(
            "total_messages",
            result,
        )