from context.tests.base import EnterpriseBaseTestCase

from knowledge.services.organization_health import (
    OrganizationHealthService,
)


class OrganizationHealthTests(
    EnterpriseBaseTestCase,
):

    def setUp(self):

        super().setUp()

        self.service = (
            OrganizationHealthService()
        )

    def test_total(self):

        result = self.service.build(
            organization=self.organization,
        )

        self.assertEqual(
            result["total"],
            2,
        )

    def test_healthy_exists(self):

        result = self.service.build(
            organization=self.organization,
        )

        self.assertIn(
            "healthy",
            result,
        )

    def test_moderate_exists(self):

        result = self.service.build(
            organization=self.organization,
        )

        self.assertIn(
            "moderate",
            result,
        )

    def test_risk_exists(self):

        result = self.service.build(
            organization=self.organization,
        )

        self.assertIn(
            "risk",
            result,
        )