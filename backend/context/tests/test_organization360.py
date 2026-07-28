from context.tests.base import (
    EnterpriseBaseTestCase,
)

from knowledge.services.organization360 import (
    Organization360Service,
)


class Organization360Tests(
    EnterpriseBaseTestCase,
):

    def setUp(self):

        super().setUp()

        self.service = (
            Organization360Service()
        )

    def test_metrics_exists(self):

        result = self.service.build(
            organization=self.organization,
        )

        self.assertIn(
            "metrics",
            result,
        )

    def test_activity_exists(self):

        result = self.service.build(
            organization=self.organization,
        )

        self.assertIn(
            "activity",
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

    def test_organization_exists(self):

        result = self.service.build(
            organization=self.organization,
        )

        self.assertEqual(
            result["organization"]["name"],
            "Test Organization",
        )
    
    def test_response_contract(self):

        result = self.service.build(
            organization=self.organization,
        )

        expected = {

            "organization",

            "metrics",

            "activity",

            "health",

        }

        self.assertEqual(

            set(result.keys()),

            expected,

        )