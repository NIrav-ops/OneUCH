"""
Enterprise Person Resolver
"""

from context.services.person_repository import (
    PersonRepository,
)


class PersonResolver:
    """
    Resolves communication participants into Person entities.
    """

    def __init__(self):

        self.repository = PersonRepository()

    def resolve(
        self,
        *,
        organization,
        email,
        full_name="",
        company="",
    ):

        if not email:
            return None

        person, created = self.repository.get_or_create(
            organization=organization,
            email=email,
            defaults={
                "full_name": full_name,
                "company": company,
            },
        )

        updated = False

        if full_name and not person.full_name:
            person.full_name = full_name
            updated = True

        if company and not person.company:
            person.company = company
            updated = True

        if updated:
            person.save(
                update_fields=[
                    "full_name",
                    "company",
                    "updated_at",
                ]
            )

        return person