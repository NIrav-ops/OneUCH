from context.tests.base import EnterpriseBaseTestCase

from context.models import Person

from knowledge.services.person_metrics import (
    PersonMetricsService,
)


class PersonMetricsTests(
    EnterpriseBaseTestCase,
):

    def setUp(self):

        super().setUp()

        self.person = Person.objects.create(
            organization=self.organization,
            email="john@example.com",
            full_name="John Smith",
        )

        self.evidence.person = self.person
        self.evidence.save()

        self.service = PersonMetricsService()

    def test_total(self):

        result = self.service.build(
            person=self.person,
        )

        self.assertEqual(
            result["total_evidence"],
            1,
        )

    def test_email_count(self):

        result = self.service.build(
            person=self.person,
        )

        self.assertEqual(
            result["emails"],
            1,
        )

    def test_last_activity(self):

        result = self.service.build(
            person=self.person,
        )

        self.assertIsNotNone(
            result["last_activity"],
        )

    def test_metrics_contract(self):

        result = self.service.build(
            person=self.person,
        )

        expected = {

            "total_evidence",
            "emails",
            "meetings",
            "tasks",
            "documents",
            "approvals",
            "last_activity",

        }

        self.assertEqual(
            set(result.keys()),
            expected,
        )