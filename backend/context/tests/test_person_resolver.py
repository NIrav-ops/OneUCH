from context.tests.base import EnterpriseBaseTestCase

from context.services.person_resolver import (
    PersonResolver,
)


class PersonResolverTests(
    EnterpriseBaseTestCase,
):

    def setUp(self):

        super().setUp()

        self.resolver = PersonResolver()

    def test_create_person(self):

        person = self.resolver.resolve(
            organization=self.organization,
            email="john@example.com",
        )

        self.assertEqual(
            person.email,
            "john@example.com",
        )

    def test_existing_person(self):

        self.resolver.resolve(
            organization=self.organization,
            email="john@example.com",
        )

        person = self.resolver.resolve(
            organization=self.organization,
            email="john@example.com",
        )

        self.assertEqual(
            person.email,
            "john@example.com",
        )

    def test_full_name(self):

        person = self.resolver.resolve(
            organization=self.organization,
            email="john@example.com",
            full_name="John Smith",
        )

        self.assertEqual(
            person.full_name,
            "John Smith",
        )

    def test_company(self):

        person = self.resolver.resolve(
            organization=self.organization,
            email="john@example.com",
            company="Google",
        )

        self.assertEqual(
            person.company,
            "Google",
        )

    def test_none_email(self):

        person = self.resolver.resolve(
            organization=self.organization,
            email="",
        )

        self.assertIsNone(person)