from django.conf import (
    settings,
)

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from django.db import (
    connection,
)

from backend.pilot_release_gate import (
    collect_pilot_release_errors,
)


class Command(BaseCommand):

    help = (
        "Run the final One UCH pilot deployment "
        "security and runtime readiness gate."
    )

    requires_system_checks = []


    def handle(
        self,
        *args,
        **options,
    ):

        errors = (
            collect_pilot_release_errors(
                settings_obj=settings,
                connection_obj=connection,
                redis_client=(
                    settings.REDIS_CLIENT
                ),
            )
        )


        if errors:

            self.stderr.write(
                "One UCH pilot release gate FAILED:"
            )

            for error in errors:

                self.stderr.write(
                    f" - {error}"
                )


            raise CommandError(
                "Pilot release verification failed."
            )


        self.stdout.write(
            self.style.SUCCESS(
                "PASS - One UCH pilot release "
                "security gate is green."
            )
        )
