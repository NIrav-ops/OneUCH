
from django.contrib.auth import (
    get_user_model,
)

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from backend.pilot_user_gate import (
    collect_pilot_user_errors,
)

from email_accounts.models import (
    EmailAccount,
)

from inbox.models import (
    InboxSyncStatus,
    OrganizationUser,
)

from oauth_tokens.models import (
    OAuthToken,
)


class Command(BaseCommand):

    help = (
        "Verify that a selected One UCH pilot user "
        "is ready for real-user acceptance."
    )


    def add_arguments(
        self,
        parser,
    ):

        parser.add_argument(
            "--email",
            required=True,
            help=(
                "Email address of the selected "
                "pilot user."
            ),
        )


    def handle(
        self,
        *args,
        **options,
    ):

        errors = (
            collect_pilot_user_errors(
                email=options["email"],
                user_model=get_user_model(),
                organization_user_model=(
                    OrganizationUser
                ),
                email_account_model=(
                    EmailAccount
                ),
                oauth_token_model=(
                    OAuthToken
                ),
                sync_status_model=(
                    InboxSyncStatus
                ),
            )
        )


        if errors:

            self.stderr.write(
                "One UCH pilot user gate FAILED:"
            )

            for error in errors:

                self.stderr.write(
                    f" - {error}"
                )


            raise CommandError(
                "Selected pilot user is not "
                "ready for release."
            )


        self.stdout.write(
            self.style.SUCCESS(
                "PASS - selected One UCH pilot "
                "user is ready for real-user acceptance."
            )
        )
