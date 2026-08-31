
from datetime import (
    timedelta,
)

from io import (
    StringIO,
)

from pathlib import (
    Path,
)

from django.contrib.auth import (
    get_user_model,
)

from django.core.management import (
    call_command,
)

from django.core.management.base import (
    CommandError,
)

from django.test import (
    TestCase,
)

from django.utils import (
    timezone,
)

from backend.pilot_user_gate import (
    collect_pilot_user_errors,
)

from email_accounts.models import (
    EmailAccount,
)

from inbox.models import (
    InboxSyncStatus,
    Organization,
    OrganizationUser,
)

from oauth_tokens.models import (
    OAuthToken,
)


User = get_user_model()


class PilotUserGateTests(
    TestCase
):

    def setUp(
        self,
    ):

        self.password = (
            "PilotPassword123!"
        )

        self.user = (
            User.objects.create_user(
                email=(
                    "pilot-user@oneuch.test"
                ),
                password=self.password,
            )
        )

        self.organization = (
            Organization.objects.create(
                name="Pilot Organization",
                slug="pilot-organization",
            )
        )

        self.membership = (
            OrganizationUser.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                role="member",
            )
        )


    def errors(
        self,
        email=None,
    ):

        return collect_pilot_user_errors(
            email=(
                email
                if email is not None
                else self.user.email
            ),
            user_model=User,
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


    def connect(
        self,
        *,
        account_type="gmail",
        token_active=True,
        disabled_by_admin=False,
        refresh_token="refresh-token",
        expires_at=None,
    ):

        EmailAccount.objects.create(
            user=self.user,
            account_type=account_type,
            email_address=(
                "mailbox@oneuch.test"
            ),
            is_active=True,
        )

        provider = (
            "google"
            if account_type == "gmail"
            else "microsoft"
        )

        OAuthToken.objects.create(
            user=self.user,
            provider=provider,
            access_token="test-access-token",
            refresh_token=refresh_token,
            expires_at=(
                expires_at
                or (
                    timezone.now()
                    + timedelta(hours=1)
                )
            ),
            is_active=token_active,
            disabled_by_admin=(
                disabled_by_admin
            ),
        )


    def successful_sync(
        self,
        *,
        platform="gmail",
    ):

        InboxSyncStatus.objects.create(
            user=self.user,
            platform=platform,
            status="success",
            progress=100,
            last_synced_at=(
                timezone.now()
            ),
        )


    def test_ready_gmail_user_passes(
        self,
    ):

        self.connect(
            account_type="gmail"
        )

        self.successful_sync(
            platform="gmail"
        )

        self.assertEqual(
            self.errors(),
            [],
        )


    def test_ready_outlook_user_passes(
        self,
    ):

        self.connect(
            account_type="outlook"
        )

        self.successful_sync(
            platform="outlook"
        )

        self.assertEqual(
            self.errors(),
            [],
        )


    def test_missing_user_fails(
        self,
    ):

        self.assertIn(
            (
                "Selected pilot user "
                "does not exist."
            ),
            self.errors(
                email=(
                    "missing@oneuch.test"
                )
            ),
        )


    def test_inactive_user_fails(
        self,
    ):

        self.user.is_active = False

        self.user.save(
            update_fields=[
                "is_active",
            ]
        )

        self.assertIn(
            (
                "Selected pilot user "
                "must be active."
            ),
            self.errors(),
        )


    def test_missing_membership_fails(
        self,
    ):

        self.membership.delete()

        self.assertIn(
            (
                "Selected pilot user must "
                "have an organization membership."
            ),
            self.errors(),
        )


    def test_inactive_organization_fails(
        self,
    ):

        self.organization.is_active = False

        self.organization.save(
            update_fields=[
                "is_active",
            ]
        )

        self.assertIn(
            (
                "Selected pilot user's "
                "organization must be active."
            ),
            self.errors(),
        )


    def test_missing_mailbox_fails(
        self,
    ):

        self.assertIn(
            (
                "Selected pilot user must have "
                "at least one active Gmail or "
                "Outlook account."
            ),
            self.errors(),
        )


    def test_missing_oauth_authorization_fails(
        self,
    ):

        EmailAccount.objects.create(
            user=self.user,
            account_type="gmail",
            email_address=(
                "mailbox@oneuch.test"
            ),
            is_active=True,
        )

        self.assertIn(
            (
                "Selected pilot user must have "
                "a usable Google or Microsoft "
                "OAuth authorization."
            ),
            self.errors(),
        )


    def test_expired_token_without_refresh_fails(
        self,
    ):

        self.connect(
            expires_at=(
                timezone.now()
                - timedelta(minutes=5)
            ),
            refresh_token=None,
        )

        self.assertIn(
            (
                "Selected pilot user must have "
                "a usable Google or Microsoft "
                "OAuth authorization."
            ),
            self.errors(),
        )


    def test_expired_token_with_refresh_is_refreshable(
        self,
    ):

        self.connect(
            expires_at=(
                timezone.now()
                - timedelta(minutes=5)
            ),
            refresh_token="refresh-token",
        )

        self.successful_sync()

        self.assertEqual(
            self.errors(),
            [],
        )


    def test_admin_disabled_token_fails(
        self,
    ):

        self.connect(
            disabled_by_admin=True
        )

        self.assertIn(
            (
                "Selected pilot user must have "
                "a usable Google or Microsoft "
                "OAuth authorization."
            ),
            self.errors(),
        )


    def test_successful_sync_is_required(
        self,
    ):

        self.connect()

        self.assertIn(
            (
                "Selected pilot user must complete "
                "at least one successful Gmail or "
                "Outlook synchronization."
            ),
            self.errors(),
        )


    def test_management_command_passes_ready_user(
        self,
    ):

        self.connect()
        self.successful_sync()

        stdout = StringIO()

        call_command(
            "verify_pilot_user",
            email=self.user.email,
            stdout=stdout,
        )

        self.assertIn(
            "PASS - selected One UCH pilot user",
            stdout.getvalue(),
        )


    def test_management_command_blocks_unready_user(
        self,
    ):

        with self.assertRaises(
            CommandError
        ):

            call_command(
                "verify_pilot_user",
                email=self.user.email,
                stdout=StringIO(),
                stderr=StringIO(),
            )


    def test_pilot_runbook_matches_hardened_topology(
        self,
    ):

        repo_root = (
            Path(__file__)
            .resolve()
            .parents[2]
        )

        runbook = (
            repo_root
            / "backend"
            / "PILOT_RUNBOOK.md"
        ).read_text(
            encoding="utf-8-sig"
        )

        self.assertIn(
            "backend/.env.pilot.example",
            runbook,
        )

        self.assertIn(
            "verify_pilot_release",
            runbook,
        )

        self.assertIn(
            "verify_pilot_user",
            runbook,
        )

        self.assertIn(
            "deployment/pilot/README.md",
            runbook,
        )

        self.assertNotIn(
            "manage.py runserver",
            runbook,
        )

        self.assertNotIn(
            "--pool=solo",
            runbook,
        )

        self.assertIn(
            "/opt/oneuch/backend",
            runbook,
        )

        self.assertIn(
            "/opt/oneuch/frontend",
            runbook,
        )

        self.assertIn(
            (
                "./venv/bin/python manage.py "
                "verify_pilot_release"
            ),
            runbook,
        )

        self.assertIn(
            (
                "./venv/bin/python manage.py "
                "verify_pilot_user"
            ),
            runbook,
        )

        self.assertNotIn(
            "D:\\UnifiedMessenger",
            runbook,
        )

        self.assertNotIn(
            "\\venv\\Scripts\\python.exe",
            runbook,
        )
