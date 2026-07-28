from context.models import Person


class PersonRepository:
    """
    Repository for enterprise Person entities.
    """

    @staticmethod
    def get_by_email(
        *,
        organization,
        email,
    ):

        return Person.objects.filter(
            organization=organization,
            email__iexact=email,
        ).first()

    @staticmethod
    def get_or_create(
        *,
        organization,
        email,
        defaults=None,
    ):

        defaults = defaults or {}

        person, created = Person.objects.get_or_create(
            organization=organization,
            email=email.lower(),
            defaults=defaults,
        )

        return person, created

    @staticmethod
    def update(
        *,
        person,
        **fields,
    ):

        for key, value in fields.items():

            setattr(
                person,
                key,
                value,
            )

        person.save()

        return person

    @staticmethod
    def all_for_organization(
        *,
        organization,
    ):

        return Person.objects.filter(
            organization=organization,
        )