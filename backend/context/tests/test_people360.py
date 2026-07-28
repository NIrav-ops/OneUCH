from context.tests.base import (
    EnterpriseBaseTestCase,
)

from context.models import Person

from knowledge.services.people360 import (
    People360Service,
)


class People360Tests(
    EnterpriseBaseTestCase,
):

    def setUp(self):

        super().setUp()

        self.person = Person.objects.create(
            organization=self.organization,
            email="john@example.com",
            full_name="John Smith",
            company="Google",
        )

        self.evidence.person = self.person
        self.evidence.save()

        self.service = People360Service()

    def test_person_exists(self):

        result = self.service.build(
            person=self.person,
        )

        self.assertIn(
            "person",
            result,
        )

    def test_timeline_exists(self):

        result = self.service.build(
            person=self.person,
        )

        self.assertIn(
            "timeline",
            result,
        )

    def test_metrics_exists(self):

        result = self.service.build(
            person=self.person,
        )

        self.assertIn(
            "metrics",
            result,
        )

    def test_health_exists(self):

        result = self.service.build(
            person=self.person,
        )

        self.assertIn(
            "health",
            result,
        )

    def test_person_name(self):

        result = self.service.build(
            person=self.person,
        )

        self.assertEqual(
            result["person"]["full_name"],
            "John Smith",
        )

    def test_company(self):

        result = self.service.build(
            person=self.person,
        )

        self.assertEqual(
            result["person"]["company"],
            "Google",
        )

    def test_contract(self):

        result = self.service.build(
            person=self.person,
        )

        expected = {

            "person",
            "timeline",
            "metrics",
            "health",

        }

        self.assertEqual(

            set(result.keys()),

            expected,

        )
    