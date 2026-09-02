from django.contrib.auth import (
    get_user_model,
)

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from context.services.communication_identity_bootstrap import (
    bootstrap_communication_identities,
    build_communication_identity_plan,
)


User = get_user_model()


class Command(BaseCommand):
    help = (
        "Bootstrap Person and DISCOVERED Company identity "
        "context from the governed recipient directory."
    )

    def add_arguments(
        self,
        parser,
    ):
        parser.add_argument(
            "--user-id",
            type=int,
            required=True,
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
        )

    def handle(
        self,
        *args,
        **options,
    ):
        user_id = options["user_id"]

        try:
            user = User.objects.get(
                pk=user_id
            )

        except User.DoesNotExist as exc:
            raise CommandError(
                "User does not exist."
            ) from exc

        if options["dry_run"]:
            plan = (
                build_communication_identity_plan(
                    user=user
                )
            )

            summary = plan["summary"]

            self.stdout.write(
                "COMMUNICATION IDENTITY BOOTSTRAP DRY RUN"
            )

            self.stdout.write(
                "RECIPIENT_CONTACTS="
                + str(
                    summary[
                        "recipient_contacts"
                    ]
                )
            )

            self.stdout.write(
                "HUMAN_CONTACTS="
                + str(
                    summary[
                        "human_contacts"
                    ]
                )
            )

            self.stdout.write(
                "MACHINE_CONTACTS="
                + str(
                    summary[
                        "machine_contacts"
                    ]
                )
            )

            self.stdout.write(
                "QUALIFIED_BUSINESS_DOMAINS="
                + str(
                    summary[
                        "qualified_business_domains"
                    ]
                )
            )

            self.stdout.write(
                "QUALIFIED_HUMAN_CONTACTS="
                + str(
                    summary[
                        "qualified_human_contacts"
                    ]
                )
            )

            self.stdout.write(
                self.style.SUCCESS(
                    "PASS - dry-run plan complete."
                )
            )

            return

        result = (
            bootstrap_communication_identities(
                user=user
            )
        )

        self.stdout.write(
            "COMMUNICATION IDENTITY BOOTSTRAP"
        )

        keys = (
            "recipient_contacts",
            "human_contacts",
            "machine_contacts",
            "qualified_business_domains",
            "qualified_human_contacts",
            "people_created",
            "people_updated",
            "business_objects_created",
            "domain_identities_created",
            "email_identities_created",
            "total_people",
            "total_business_objects",
            "total_business_identities",
        )

        for key in keys:
            self.stdout.write(
                key.upper()
                + "="
                + str(
                    result[key]
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                "PASS - communication identity bootstrap complete."
            )
        )