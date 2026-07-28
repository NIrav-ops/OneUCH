from context.tests.base import EnterpriseBaseTestCase

from context.models import Person

from context.services.person_repository import (
    PersonRepository,
)


class PersonRepositoryTests(
    EnterpriseBaseTestCase,
):

    def setUp(self):

        super().setUp()

        self.repo = PersonRepository()

    def test_create_person(self):

        person, created = self.repo.get_or_create(
            organization=self.organization,
            email="john@example.com",
        )

        self.assertTrue(created)

        self.assertEqual(
            person.email,
            "john@example.com",
        )

    def test_get_existing(self):

        self.repo.get_or_create(
            organization=self.organization,
            email="john@example.com",
        )

        person = self.repo.get_by_email(
            organization=self.organization,
            email="john@example.com",
        )

        self.assertIsNotNone(person)

    def test_update(self):

        person, _ = self.repo.get_or_create(
            organization=self.organization,
            email="john@example.com",
        )

        self.repo.update(
            person=person,
            full_name="John Smith",
        )

        person.refresh_from_db()

        self.assertEqual(
            person.full_name,
            "John Smith",
        )

    def test_all_people(self):

        self.repo.get_or_create(
            organization=self.organization,
            email="john@example.com",
        )

        people = self.repo.all_for_organization(
            organization=self.organization,
        )

        self.assertEqual(
            people.count(),
            1,
        )