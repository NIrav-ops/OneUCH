from context.tests.base import EnterpriseBaseTestCase

from knowledge.services.communication_analytics import (
    CommunicationAnalyticsService,
)


class CommunicationAnalyticsTests(
    EnterpriseBaseTestCase,
):

    def setUp(self):

        super().setUp()

        self.service = (
            CommunicationAnalyticsService()
        )

    def test_total_messages(self):

        result = self.service.build(
            organization=self.organization,
        )

        self.assertEqual(
            result["total_messages"],
            1,
        )

    def test_gmail(self):

        result = self.service.build(
            organization=self.organization,
        )

        self.assertEqual(
            result["gmail"],
            1,
        )

    def test_contract(self):

        result = self.service.build(
            organization=self.organization,
        )

        expected = {

            "total_messages",

            "gmail",

            "outlook",

            "teams",

            "imap",

        }

        self.assertEqual(
            set(result.keys()),
            expected,
        )

    def test_outlook_zero(self):

        result = self.service.build(
            organization=self.organization,
        )

        self.assertEqual(
            result["outlook"],
            0,
        )