from django.conf import (
    settings,
)

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from backend.deployment_validation import (
    collect_pilot_configuration_errors,
)


class Command(BaseCommand):
    help = (
        "Validate the One UCH pilot deployment "
        "security configuration."
    )

    requires_system_checks = []


    def handle(
        self,
        *args,
        **options,
    ):
        errors = (
            collect_pilot_configuration_errors(
                settings
            )
        )

        if errors:

            self.stderr.write(
                "One UCH pilot environment is NOT ready:"
            )

            for error in errors:
                self.stderr.write(
                    f" - {error}"
                )

            raise CommandError(
                "Pilot environment validation failed."
            )


        self.stdout.write(
            self.style.SUCCESS(
                "PASS - One UCH pilot environment "
                "configuration is secure."
            )
        )
