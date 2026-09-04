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
from inbox.models import (
    Organization,
    OrganizationUser,
)


class AuthSecRC1AA2Tests(
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
        active_workspace=True,
    ):

        user = (
            User.objects.create_user(
                email=email,
                password=self.PASSWORD,
                signup_method=(
                    AUTH_METHOD_WORK_EMAIL
                ),
            )
        )

        organization = (
            Organization.objects.create(
                name="Private Workspace",
                slug=(
                    "workspace-"
                    + uuid4().hex
                ),
                is_active=(
                    active_workspace
                ),
            )
        )

        OrganizationUser.objects.create(
            user=user,
            organization=organization,
            role="owner",
        )

        return (
            user,
            organization,
        )

    @override_settings(
        AUTH_SELF_SERVICE_SIGNUP_ENABLED=False
    )
    def test_signup_fails_closed_by_default(
        self,
    ):

        response = self.client.post(
            "/api/auth/signup/",
            {
                "email": (
                    "blocked@example.test"
                ),
                "password": self.PASSWORD,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertFalse(
            User.objects.filter(
                email=(
                    "blocked@example.test"
                )
            ).exists()
        )

    @override_settings(
        AUTH_SELF_SERVICE_SIGNUP_ENABLED=True
    )
    def test_signup_creates_private_owner_workspace(
        self,
    ):

        response = self.client.post(
            "/api/auth/signup/",
            {
                "email": (
                    "first@example.test"
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
            email="first@example.test"
        )

        membership = (
            user.organization_membership
        )

        self.assertEqual(
            membership.role,
            "owner",
        )

        self.assertTrue(
            user.public_id.startswith(
                "USR-"
            )
        )

        self.assertTrue(
            membership.organization
            .public_id.startswith(
                "WSP-"
            )
        )

        self.assertNotIn(
            "access",
            response.data,
        )

        self.assertNotIn(
            "refresh",
            response.data,
        )

    @override_settings(
        AUTH_SELF_SERVICE_SIGNUP_ENABLED=True
    )
    def test_same_domain_users_get_different_workspaces(
        self,
    ):

        first = self.client.post(
            "/api/auth/signup/",
            {
                "email": (
                    "one@company.test"
                ),
                "password": self.PASSWORD,
            },
            format="json",
        )

        second = self.client.post(
            "/api/auth/signup/",
            {
                "email": (
                    "two@company.test"
                ),
                "password": (
                    "OneUCH!Secure28461"
                ),
            },
            format="json",
        )

        self.assertEqual(
            first.status_code,
            201,
        )

        self.assertEqual(
            second.status_code,
            201,
        )

        user_one = User.objects.get(
            email="one@company.test"
        )

        user_two = User.objects.get(
            email="two@company.test"
        )

        self.assertNotEqual(
            (
                user_one
                .organization_membership
                .organization_id
            ),
            (
                user_two
                .organization_membership
                .organization_id
            ),
        )

    @override_settings(
        AUTH_SELF_SERVICE_SIGNUP_ENABLED=True
    )
    def test_signup_email_is_normalized(
        self,
    ):

        response = self.client.post(
            "/api/auth/signup/",
            {
                "email": (
                    "Mixed@Example.TEST"
                ),
                "password": self.PASSWORD,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertTrue(
            User.objects.filter(
                email=(
                    "mixed@example.test"
                )
            ).exists()
        )

    def test_legacy_login_is_case_insensitive(
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
                    "LOGIN@EXAMPLE.TEST"
                ),
                "password": self.PASSWORD,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertIn(
            "access",
            response.data,
        )

        user.refresh_from_db()

        self.assertEqual(
            user.last_auth_method,
            AUTH_METHOD_WORK_EMAIL,
        )

        self.assertIsNotNone(
            user.last_login
        )

    def test_simplejwt_login_is_governed(
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
                    "TOKEN@EXAMPLE.TEST"
                ),
                "password": self.PASSWORD,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertIn(
            "access",
            response.data,
        )

        user.refresh_from_db()

        self.assertEqual(
            user.last_auth_method,
            AUTH_METHOD_WORK_EMAIL,
        )

    def test_me_uses_authenticated_private_workspace(
        self,
    ):

        user, organization = (
            self.create_private_user(
                email=(
                    "me@example.test"
                )
            )
        )

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

        response = self.client.get(
            "/api/auth/me/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["user_id"],
            user.public_id,
        )

        self.assertEqual(
            response.data[
                "workspace_id"
            ],
            organization.public_id,
        )

        self.assertEqual(
            response.data["email"],
            user.email,
        )

    def test_orphan_jwt_fails_closed(
        self,
    ):

        user = (
            User.objects.create_user(
                email=(
                    "orphan@example.test"
                ),
                password=self.PASSWORD,
            )
        )

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

        response = self.client.get(
            "/api/auth/me/"
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_inactive_workspace_jwt_fails_closed(
        self,
    ):

        user, _ = (
            self.create_private_user(
                email=(
                    "inactive@example.test"
                ),
                active_workspace=False,
            )
        )

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

        response = self.client.get(
            "/api/auth/me/"
        )

        self.assertEqual(
            response.status_code,
            401,
        )
