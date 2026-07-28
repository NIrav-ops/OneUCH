from context.tests.base import EnterpriseBaseTestCase

from knowledge.services.communication_trends import (
    CommunicationTrendService,
)


class CommunicationTrendTests(
    EnterpriseBaseTestCase,
):

    def setUp(self):

        super().setUp()

        self.service = (
            CommunicationTrendService()
        )

    def test_days_exist(self):

        result = self.service.build(
            organization=self.organization,
        )

        self.assertGreaterEqual(
            len(result["days"]),
            1,
        )

    def test_total_days(self):

        result = self.service.build(
            organization=self.organization,
        )

        self.assertEqual(
            result["total_days"],
            1,
        )

    def test_messages(self):

        result = self.service.build(
            organization=self.organization,
        )

        self.assertEqual(
            result["days"][0]["messages"],
            1,
        )

    def test_contract(self):

        result = self.service.build(
            organization=self.organization,
        )

        expected = {

            "days",
            "total_days",

        }

        self.assertEqual(
            set(result.keys()),
            expected,
        )