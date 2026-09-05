from unittest.mock import (
    Mock,
    patch,
)
from uuid import uuid4

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import (
    RefreshToken,
)

from accounts.models import (
    AUTH_METHOD_GOOGLE,
    AUTH_METHOD_LEGACY,
    AUTH_METHOD_MICROSOFT,
    AUTH_METHOD_WORK_EMAIL,
    User,
)

from email_accounts.models import (
    EmailAccount,
)

from inbox.models import (
    Organization,
    OrganizationUser,
)

from oauth_tokens.models import (
    OAuthToken,
)

from oauth_tokens.oauth_state import (
    create_oauth_state,
)


class MailRC1A2IdentityBoundaryTests(
    TestCase
):

    PASSWORD = (
        "OneUCH!MailRC1A2Secure93471"
    )

    def setUp(
        self,
    ):
        self.client = APIClient()

    def create_user(
        self,
        *,
        email,
        signup_method,
        with_workspace=True,
        active_workspace=True,
    ):
        user = User.objects.create_user(
            email=email,
            password=self.PASSWORD,
            signup_method=signup_method,
        )

        organization = None

        if with_workspace:
            organization = (
                Organization.objects.create(
                    name="Private Workspace",
                    slug=(
                        "mail-a2-"
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

    def jwt_client(
        self,
        user,
    ):
        token = (
            RefreshToken.for_user(
                user
            ).access_token
        )

        client = APIClient()

        client.credentials(
            HTTP_AUTHORIZATION=(
                "Bearer "
                + str(token)
            )
        )

        return client

    # ========================================================
    # PASSING CONTROLS
    # ========================================================

    def test_work_email_identity_can_use_password_login(
        self,
    ):
        self.create_user(
            email=(
                "work-email@oneuch.test"
            ),
            signup_method=(
                AUTH_METHOD_WORK_EMAIL
            ),
        )

        response = self.client.post(
            "/api/auth/token/",
            {
                "email":
                    "WORK-EMAIL@ONEUCH.TEST",

                "password":
                    self.PASSWORD,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_legacy_identity_remains_password_compatible(
        self,
    ):
        self.create_user(
            email=(
                "legacy@oneuch.test"
            ),
            signup_method=(
                AUTH_METHOD_LEGACY
            ),
        )

        response = self.client.post(
            "/api/auth/token/",
            {
                "email":
                    "legacy@oneuch.test",

                "password":
                    self.PASSWORD,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    # ========================================================
    # WORK-EMAIL METHOD BOUNDARY
    # ========================================================

    def test_google_identity_cannot_fall_back_to_work_email_password(
        self,
    ):
        self.create_user(
            email=(
                "google-identity@oneuch.test"
            ),
            signup_method=(
                AUTH_METHOD_GOOGLE
            ),
        )

        response = self.client.post(
            "/api/auth/token/",
            {
                "email":
                    "google-identity@oneuch.test",

                "password":
                    self.PASSWORD,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_microsoft_identity_cannot_fall_back_to_work_email_password(
        self,
    ):
        self.create_user(
            email=(
                "microsoft-identity@oneuch.test"
            ),
            signup_method=(
                AUTH_METHOD_MICROSOFT
            ),
        )

        response = self.client.post(
            "/api/auth/token/",
            {
                "email":
                    "microsoft-identity@oneuch.test",

                "password":
                    self.PASSWORD,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    # ========================================================
    # OAUTH START ACTIVE-WORKSPACE BOUNDARY
    # ========================================================

    def test_google_oauth_start_rejects_orphan_jwt(
        self,
    ):
        user, _ = self.create_user(
            email=(
                "google-orphan@oneuch.test"
            ),
            signup_method=(
                AUTH_METHOD_WORK_EMAIL
            ),
            with_workspace=False,
        )

        response = (
            self.jwt_client(
                user
            )
            .get(
                "/api/google/oauth/start/"
            )
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_microsoft_oauth_start_rejects_orphan_jwt(
        self,
    ):
        user, _ = self.create_user(
            email=(
                "microsoft-orphan@oneuch.test"
            ),
            signup_method=(
                AUTH_METHOD_WORK_EMAIL
            ),
            with_workspace=False,
        )

        response = (
            self.jwt_client(
                user
            )
            .get(
                "/api/microsoft/oauth/start/"
            )
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_google_oauth_start_rejects_inactive_workspace(
        self,
    ):
        user, _ = self.create_user(
            email=(
                "google-inactive@oneuch.test"
            ),
            signup_method=(
                AUTH_METHOD_WORK_EMAIL
            ),
            active_workspace=False,
        )

        response = (
            self.jwt_client(
                user
            )
            .get(
                "/api/google/oauth/start/"
            )
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_microsoft_oauth_start_rejects_inactive_workspace(
        self,
    ):
        user, _ = self.create_user(
            email=(
                "microsoft-inactive@oneuch.test"
            ),
            signup_method=(
                AUTH_METHOD_WORK_EMAIL
            ),
            active_workspace=False,
        )

        response = (
            self.jwt_client(
                user
            )
            .get(
                "/api/microsoft/oauth/start/"
            )
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    # ========================================================
    # CALLBACK MOCK HELPERS
    # ========================================================

    def google_callback_attack(
        self,
        *,
        user,
    ):
        state = create_oauth_state(
            user_id=user.id,
            provider="google",
        )

        token_response = Mock()

        token_response.json.return_value = {
            "access_token":
                "synthetic-google-access",

            "refresh_token":
                "synthetic-google-refresh",

            "expires_in":
                3600,
        }

        userinfo_response = Mock()

        userinfo_response.json.return_value = {
            "email":
                "synthetic-google-mailbox@oneuch.test",
        }

        with patch(
            "googleapis.views.requests.post",
            return_value=token_response,
        ) as provider_post:

            with patch(
                "googleapis.views.requests.get",
                return_value=userinfo_response,
            ) as provider_get:

                response = self.client.get(
                    "/api/google/oauth/callback/",
                    {
                        "code":
                            "synthetic-code",

                        "state":
                            state,
                    },
                )

        return (
            response,
            provider_post,
            provider_get,
        )

    def microsoft_callback_attack(
        self,
        *,
        user,
    ):
        state = create_oauth_state(
            user_id=user.id,
            provider="microsoft",
        )

        token_response = Mock()

        token_response.json.return_value = {
            "access_token":
                "synthetic-microsoft-access",

            "refresh_token":
                "synthetic-microsoft-refresh",

            "expires_in":
                3600,
        }

        profile_response = Mock()

        profile_response.json.return_value = {
            "mail":
                "synthetic-microsoft-mailbox@oneuch.test",

            "displayName":
                "Synthetic Test User",
        }

        with patch(
            "microsoftapis.views.requests.post",
            return_value=token_response,
        ) as provider_post:

            with patch(
                "microsoftapis.views.requests.get",
                return_value=profile_response,
            ) as provider_get:

                response = self.client.get(
                    "/api/microsoft/oauth/callback/",
                    {
                        "code":
                            "synthetic-code",

                        "state":
                            state,
                    },
                )

        return (
            response,
            provider_post,
            provider_get,
        )

    # ========================================================
    # CALLBACK ACTIVE-WORKSPACE BOUNDARY
    # ========================================================

    def test_google_callback_blocks_orphan_before_provider_call(
        self,
    ):
        user, _ = self.create_user(
            email=(
                "google-callback-orphan@oneuch.test"
            ),
            signup_method=(
                AUTH_METHOD_WORK_EMAIL
            ),
            with_workspace=False,
        )

        (
            response,
            provider_post,
            provider_get,
        ) = self.google_callback_attack(
            user=user
        )

        provider_post.assert_not_called()
        provider_get.assert_not_called()

        self.assertIn(
            response.status_code,
            {
                400,
                401,
                403,
            },
        )

        self.assertFalse(
            OAuthToken.objects.filter(
                user=user,
                provider="google",
            ).exists()
        )

        self.assertFalse(
            EmailAccount.objects.filter(
                user=user,
                account_type="gmail",
            ).exists()
        )

    def test_microsoft_callback_blocks_orphan_before_provider_call(
        self,
    ):
        user, _ = self.create_user(
            email=(
                "microsoft-callback-orphan@oneuch.test"
            ),
            signup_method=(
                AUTH_METHOD_WORK_EMAIL
            ),
            with_workspace=False,
        )

        (
            response,
            provider_post,
            provider_get,
        ) = self.microsoft_callback_attack(
            user=user
        )

        provider_post.assert_not_called()
        provider_get.assert_not_called()

        self.assertIn(
            response.status_code,
            {
                400,
                401,
                403,
            },
        )

        self.assertFalse(
            OAuthToken.objects.filter(
                user=user,
                provider="microsoft",
            ).exists()
        )

        self.assertFalse(
            EmailAccount.objects.filter(
                user=user,
                account_type="outlook",
            ).exists()
        )

    def test_google_callback_blocks_inactive_workspace_before_provider_call(
        self,
    ):
        user, _ = self.create_user(
            email=(
                "google-callback-inactive@oneuch.test"
            ),
            signup_method=(
                AUTH_METHOD_WORK_EMAIL
            ),
            active_workspace=False,
        )

        (
            response,
            provider_post,
            provider_get,
        ) = self.google_callback_attack(
            user=user
        )

        provider_post.assert_not_called()
        provider_get.assert_not_called()

        self.assertIn(
            response.status_code,
            {
                400,
                401,
                403,
            },
        )

    def test_microsoft_callback_blocks_inactive_workspace_before_provider_call(
        self,
    ):
        user, _ = self.create_user(
            email=(
                "microsoft-callback-inactive@oneuch.test"
            ),
            signup_method=(
                AUTH_METHOD_WORK_EMAIL
            ),
            active_workspace=False,
        )

        (
            response,
            provider_post,
            provider_get,
        ) = self.microsoft_callback_attack(
            user=user
        )

        provider_post.assert_not_called()
        provider_get.assert_not_called()

        self.assertIn(
            response.status_code,
            {
                400,
                401,
                403,
            },
        )
