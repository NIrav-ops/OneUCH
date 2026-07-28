from context.tests.base import EnterpriseBaseTestCase

from context.models import Person

from knowledge.services.person_timeline import (
    PersonTimelineService,
)


class PersonTimelineTests(
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

        self.service = PersonTimelineService()

    def test_timeline_exists(self):

        result = self.service.build(
            person=self.person,
        )

        self.assertEqual(
            len(result),
            1,
        )

    def test_title(self):

        result = self.service.build(
            person=self.person,
        )

        self.assertEqual(
            result[0]["title"],
            "Enterprise Test",
        )

    def test_channel(self):

        result = self.service.build(
            person=self.person,
        )

        self.assertEqual(
            result[0]["channel"],
            "gmail",
        )

    def test_confidence(self):

        result = self.service.build(
            person=self.person,
        )

        self.assertEqual(
            result[0]["confidence"],
            95,
        )