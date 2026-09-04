import json
from uuid import uuid4

from django.test import (
    TestCase,
    override_settings,
)
from rest_framework.test import (
    APIClient,
)
from rest_framework_simplejwt.tokens import (
    RefreshToken,
)

from accounts.models import (
    AUTH_METHOD_WORK_EMAIL,
    User,
)
from email_accounts.models import (
    EmailAccount,
)
from inbox.models import (
    AuditLog,
    Organization,
    OrganizationUser,
)


@override_settings(
    AUTH_SELF_SERVICE_SIGNUP_ENABLED=True,
    ONEUCH_ENVIRONMENT="test",
    ONEUCH_REGION="test-region",
)
class AuthSecRC1AA3Tests(
    TestCase
):

    PASSWORD = (
        "OneUCH!Secure93471"
    )

    def setUp(
        self,
    ):

        self.client = APIClient()

    def create_private_user(
        self,
        *,
        email,
        is_staff=False,
    ):

        user = (
            User.objects.create_user(
                email=email,
                password=self.PASSWORD,
                signup_method=(
                    AUTH_METHOD_WORK_EMAIL
                ),
                is_staff=is_staff,
            )
        )

        workspace = (
            Organization.objects.create(
                name="Private Workspace",
                slug=(
                    "workspace-"
                    + uuid4().hex
                ),
            )
        )

        OrganizationUser.objects.create(
            user=user,
            organization=workspace,
            role="owner",
        )

        return (
            user,
            workspace,
        )

    def authenticate(
        self,
        user,
    ):

        token = (
            RefreshToken.for_user(
                user
            ).access_token
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=(
                "Bearer "
                + str(token)
            )
        )

    def test_signup_creates_minimal_audit_event(
        self,
    ):

        response = self.client.post(
            "/api/auth/signup/",
            {
                "email": (
                    "signup@example.test"
                ),
                "password": self.PASSWORD,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        user = User.objects.get(
            email="signup@example.test"
        )

        event = AuditLog.objects.get(
            user=user,
            action="SIGNUP",
        )

        self.assertEqual(
            event.metadata,
            {
                "signup_method": (
                    AUTH_METHOD_WORK_EMAIL
                ),
            },
        )

        serialized = json.dumps(
            event.metadata
        )

        self.assertNotIn(
            user.email,
            serialized,
        )

    def test_legacy_login_creates_login_audit(
        self,
    ):

        user, _ = (
            self.create_private_user(
                email=(
                    "login@example.test"
                )
            )
        )

        response = self.client.post(
            "/api/auth/login/",
            {
                "email": (
                    "login@example.test"
                ),
                "password": self.PASSWORD,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        event = (
            AuditLog.objects
            .filter(
                user=user,
                action="LOGIN",
            )
            .latest(
                "created_at"
            )
        )

        self.assertEqual(
            event.metadata,
            {
                "auth_method": (
                    AUTH_METHOD_WORK_EMAIL
                ),
            },
        )

    def test_token_login_creates_login_audit(
        self,
    ):

        user, _ = (
            self.create_private_user(
                email=(
                    "token@example.test"
                )
            )
        )

        response = self.client.post(
            "/api/auth/token/",
            {
                "email": (
                    "token@example.test"
                ),
                "password": self.PASSWORD,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            AuditLog.objects.filter(
                user=user,
                action="LOGIN",
            ).exists()
        )

    def test_staff_registry_contains_only_approved_metadata(
        self,
    ):

        customer, workspace = (
            self.create_private_user(
                email=(
                    "customer@example.test"
                )
            )
        )

        # Deliberately use a different mailbox
        # address and a secret credential so the
        # registry test proves neither leaks.

        EmailAccount.objects.create(
            user=customer,
            account_type="imap",
            email_address=(
                "private-mailbox@"
                "mailhost.test"
            ),
            smtp_password=(
                "DO-NOT-EXPOSE-THIS"
            ),
            is_active=True,
        )

        staff, _ = (
            self.create_private_user(
                email=(
                    "operator@example.test"
                ),
                is_staff=True,
            )
        )

        self.authenticate(
            staff
        )

        response = self.client.get(
            (
                "/api/auth/platform/"
                "signup-registry/"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        customer_row = next(
            row
            for row
            in response.data["users"]
            if row["email"]
            == "customer@example.test"
        )

        expected_keys = {
            "user_id",
            "email",
            "workspace_id",
            "signup_method",
            "last_auth_method",
            "signed_up_at",
            "last_sign_in_at",
            "status",
            "environment",
            "region",
            "mailbox_connected",
            "mail_providers",
        }

        self.assertEqual(
            set(
                customer_row.keys()
            ),
            expected_keys,
        )

        self.assertEqual(
            customer_row["user_id"],
            customer.public_id,
        )

        self.assertEqual(
            customer_row[
                "workspace_id"
            ],
            workspace.public_id,
        )

        self.assertEqual(
            customer_row[
                "environment"
            ],
            "test",
        )

        self.assertEqual(
            customer_row["region"],
            "test-region",
        )

        self.assertTrue(
            customer_row[
                "mailbox_connected"
            ]
        )

        self.assertEqual(
            customer_row[
                "mail_providers"
            ],
            [
                "other_work_email",
            ],
        )

        serialized = json.dumps(
            response.data
        )

        self.assertNotIn(
            (
                "private-mailbox@"
                "mailhost.test"
            ),
            serialized,
        )

        self.assertNotIn(
            "DO-NOT-EXPOSE-THIS",
            serialized,
        )

        for forbidden_key in (
            "smtp_password",
            "imap_server",
            "smtp_server",
            "subject",
            "body",
            "recipients",
            "attachment",
            "oauth_token",
            "refresh_token",
        ):

            self.assertNotIn(
                forbidden_key,
                serialized,
            )

    def test_registry_access_is_audited(
        self,
    ):

        staff, _ = (
            self.create_private_user(
                email=(
                    "staff@example.test"
                ),
                is_staff=True,
            )
        )

        self.authenticate(
            staff
        )

        response = self.client.get(
            (
                "/api/auth/platform/"
                "signup-registry/"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        event = (
            AuditLog.objects
            .filter(
                user=staff,
                action=(
                    "SIGNUP_REGISTRY_VIEW"
                ),
            )
            .latest(
                "created_at"
            )
        )

        self.assertIn(
            "returned_count",
            event.metadata,
        )

        self.assertNotIn(
            "email",
            event.metadata,
        )

    def test_non_staff_cannot_access_registry(
        self,
    ):

        user, _ = (
            self.create_private_user(
                email=(
                    "normal@example.test"
                )
            )
        )

        self.authenticate(
            user
        )

        response = self.client.get(
            (
                "/api/auth/platform/"
                "signup-registry/"
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_auth_environment_templates_use_real_line_breaks(
        self,
    ):

        from pathlib import Path

        backend_root = (
            Path(__file__)
            .resolve()
            .parents[1]
        )

        expected = {
            ".env.example": {
                (
                    "AUTH_SELF_SERVICE_"
                    "SIGNUP_ENABLED"
                ): "false",
                "ONEUCH_ENVIRONMENT": (
                    "development"
                ),
                "ONEUCH_REGION": (
                    "local"
                ),
            },
            ".env.pilot.example": {
                (
                    "AUTH_SELF_SERVICE_"
                    "SIGNUP_ENABLED"
                ): "false",
                "ONEUCH_ENVIRONMENT": (
                    "pilot"
                ),
                "ONEUCH_REGION": (
                    "replace-with-deployment-region"
                ),
            },
        }

        for (
            filename,
            required,
        ) in expected.items():

            text = (
                backend_root
                .joinpath(
                    filename
                )
                .read_text(
                    encoding="utf-8"
                )
            )

            self.assertNotIn(
                "\\nONEUCH_ENVIRONMENT=",
                text,
            )

            self.assertNotIn(
                "\\nONEUCH_REGION=",
                text,
            )

            parsed = {}

            for line in text.splitlines():

                line = line.strip()

                if (
                    not line
                    or line.startswith("#")
                    or "=" not in line
                ):
                    continue

                key, value = line.split(
                    "=",
                    1,
                )

                parsed[key] = value

            for (
                key,
                expected_value,
            ) in required.items():

                self.assertEqual(
                    parsed.get(
                        key
                    ),
                    expected_value,
                )


    def test_me_returns_provider_category_not_mailbox_address(
        self,
    ):

        user, workspace = (
            self.create_private_user(
                email=(
                    "me@example.test"
                )
            )
        )

        EmailAccount.objects.create(
            user=user,
            account_type="gmail",
            email_address=(
                "another-address@"
                "mailbox.test"
            ),
            is_active=True,
        )

        self.authenticate(
            user
        )

        response = self.client.get(
            "/api/auth/me/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data[
                "workspace_id"
            ],
            workspace.public_id,
        )

        self.assertTrue(
            response.data[
                "mailbox_connected"
            ]
        )

        self.assertEqual(
            response.data[
                "mail_providers"
            ],
            [
                "gmail",
            ],
        )

        serialized = json.dumps(
            response.data
        )

        self.assertNotIn(
            (
                "another-address@"
                "mailbox.test"
            ),
            serialized,
        )
