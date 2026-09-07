from django.core.cache import (
    cache,
)
from django.test import (
    TestCase,
    override_settings,
)

from rest_framework.test import (
    APIClient,
)

from accounts.browser_session import (
    BROWSER_CSRF_COOKIE,
    BROWSER_REFRESH_COOKIE,
    BROWSER_SESSION_COOKIE_PATH,
)
from accounts.identity_service import (
    create_identity_login_grant,
)
from accounts.models import (
    AUTH_METHOD_GOOGLE,
    AUTH_METHOD_WORK_EMAIL,
    ExternalIdentity,
    User,
)
from inbox.models import (
    Organization,
    OrganizationUser,
)


@override_settings(
    AUTH_BROWSER_SESSION_ENABLED=True,
    DEBUG=True,
)
class AuthSecRC2F2BrowserSessionTests(
    TestCase,
):

    PASSWORD = (
        "OneUCH!F2Browser93471"
    )

    def setUp(
        self,
    ):
        cache.clear()

        self.client = APIClient()

        self.user = (
            User.objects.create_user(
                email=(
                    "browser-f2@oneuch.test"
                ),
                password=self.PASSWORD,
                signup_method=(
                    AUTH_METHOD_WORK_EMAIL
                ),
            )
        )

        self.organization = (
            Organization.objects.create(
                name=(
                    "F2 Browser Workspace"
                ),
                slug=(
                    "f2-browser-workspace"
                ),
                is_active=True,
            )
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=(
                self.organization
            ),
            role="owner",
        )


    def seed_csrf(
        self,
    ):
        response = self.client.get(
            "/api/auth/session/csrf/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        token = (
            response.data[
                "csrf_token"
            ]
        )

        self.assertTrue(
            token
        )

        return token


    def session_login(
        self,
    ):
        token = self.seed_csrf()

        response = self.client.post(
            "/api/auth/session/login/",
            {
                "email":
                    self.user.email,

                "password":
                    self.PASSWORD,
            },
            format="json",
            HTTP_X_ONEUCH_CSRF=token,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        return (
            token,
            response,
        )


    @override_settings(
        AUTH_BROWSER_SESSION_ENABLED=False,
    )
    def test_browser_session_feature_is_fail_closed(
        self,
    ):
        response = self.client.get(
            "/api/auth/session/csrf/"
        )

        self.assertEqual(
            response.status_code,
            404,
        )


    def test_csrf_seed_sets_scoped_httponly_cookie_and_no_store(
        self,
    ):
        response = self.client.get(
            "/api/auth/session/csrf/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        cookie = response.cookies[
            BROWSER_CSRF_COOKIE
        ]

        self.assertTrue(
            cookie[
                "httponly"
            ]
        )

        self.assertEqual(
            cookie[
                "samesite"
            ],
            "Lax",
        )

        self.assertEqual(
            cookie[
                "path"
            ],
            BROWSER_SESSION_COOKIE_PATH,
        )

        self.assertEqual(
            response[
                "Cache-Control"
            ],
            "no-store",
        )

        self.assertNotIn(
            BROWSER_REFRESH_COOKIE,
            response.cookies,
        )


    @override_settings(
        DEBUG=False,
        ALLOWED_HOSTS=[
            "testserver",
        ],
        CORS_ALLOWED_ORIGINS=[
            "https://app.oneuch.test",
        ],
    )
    def test_production_csrf_seed_requires_allowed_origin_and_secure_cookie(
        self,
    ):
        rejected = self.client.get(
            "/api/auth/session/csrf/",
            HTTP_ORIGIN=(
                "https://evil.example"
            ),
        )

        self.assertEqual(
            rejected.status_code,
            403,
        )

        accepted = self.client.get(
            "/api/auth/session/csrf/",
            HTTP_ORIGIN=(
                "https://app.oneuch.test"
            ),
        )

        self.assertEqual(
            accepted.status_code,
            200,
        )

        cookie = accepted.cookies[
            BROWSER_CSRF_COOKIE
        ]

        self.assertTrue(
            cookie[
                "secure"
            ]
        )


    def test_password_session_login_rejects_missing_csrf(
        self,
    ):
        response = self.client.post(
            "/api/auth/session/login/",
            {
                "email":
                    self.user.email,

                "password":
                    self.PASSWORD,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertNotIn(
            BROWSER_REFRESH_COOKIE,
            response.cookies,
        )


    def test_password_session_login_returns_access_only_and_sets_refresh_cookie(
        self,
    ):
        _token, response = (
            self.session_login()
        )

        self.assertIn(
            "access",
            response.data,
        )

        self.assertNotIn(
            "refresh",
            response.data,
        )

        cookie = response.cookies[
            BROWSER_REFRESH_COOKIE
        ]

        self.assertTrue(
            cookie[
                "httponly"
            ]
        )

        self.assertEqual(
            cookie[
                "samesite"
            ],
            "Lax",
        )

        self.assertEqual(
            cookie[
                "path"
            ],
            BROWSER_SESSION_COOKIE_PATH,
        )

        self.assertEqual(
            response[
                "Cache-Control"
            ],
            "no-store",
        )


    def test_invalid_password_session_login_returns_no_refresh_cookie(
        self,
    ):
        token = self.seed_csrf()

        response = self.client.post(
            "/api/auth/session/login/",
            {
                "email":
                    self.user.email,

                "password":
                    "definitely-wrong",
            },
            format="json",
            HTTP_X_ONEUCH_CSRF=token,
        )

        self.assertEqual(
            response.status_code,
            401,
        )

        self.assertNotIn(
            BROWSER_REFRESH_COOKIE,
            response.cookies,
        )


    def test_refresh_requires_session_csrf(
        self,
    ):
        _token, _login = (
            self.session_login()
        )

        response = self.client.post(
            "/api/auth/session/refresh/",
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            403,
        )


    def test_refresh_uses_cookie_and_returns_access_only(
        self,
    ):
        token, _login = (
            self.session_login()
        )

        response = self.client.post(
            "/api/auth/session/refresh/",
            {},
            format="json",
            HTTP_X_ONEUCH_CSRF=token,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertIn(
            "access",
            response.data,
        )

        self.assertNotIn(
            "refresh",
            response.data,
        )


    def test_bootstrap_uses_cookie_and_returns_server_governed_session(
        self,
    ):
        token, _login = (
            self.session_login()
        )

        response = self.client.post(
            "/api/auth/session/bootstrap/",
            {},
            format="json",
            HTTP_X_ONEUCH_CSRF=token,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            response.data[
                "authenticated"
            ]
        )

        self.assertIn(
            "access",
            response.data,
        )

        self.assertEqual(
            response.data[
                "user_id"
            ],
            self.user.public_id,
        )

        self.assertNotIn(
            "refresh",
            response.data,
        )


    def test_invalid_refresh_cookie_is_rejected_and_cleared(
        self,
    ):
        token = self.seed_csrf()

        self.client.cookies[
            BROWSER_REFRESH_COOKIE
        ] = "invalid-refresh-token-value"

        response = self.client.post(
            "/api/auth/session/refresh/",
            {},
            format="json",
            HTTP_X_ONEUCH_CSRF=token,
        )

        self.assertEqual(
            response.status_code,
            401,
        )

        self.assertIn(
            BROWSER_REFRESH_COOKIE,
            response.cookies,
        )

        self.assertEqual(
            response.cookies[
                BROWSER_REFRESH_COOKIE
            ][
                "max-age"
            ],
            0,
        )


    def test_inactive_workspace_blocks_refresh_and_clears_cookie(
        self,
    ):
        token, _login = (
            self.session_login()
        )

        self.organization.is_active = (
            False
        )

        self.organization.save(
            update_fields=[
                "is_active",
            ]
        )

        response = self.client.post(
            "/api/auth/session/refresh/",
            {},
            format="json",
            HTTP_X_ONEUCH_CSRF=token,
        )

        self.assertEqual(
            response.status_code,
            401,
        )

        self.assertEqual(
            response.cookies[
                BROWSER_REFRESH_COOKIE
            ][
                "max-age"
            ],
            0,
        )


    def test_identity_grant_exchange_returns_access_only_and_refresh_cookie(
        self,
    ):
        identity_user = (
            User.objects.create_user(
                email=(
                    "google-f2@oneuch.test"
                ),
                password=self.PASSWORD,
                signup_method=(
                    AUTH_METHOD_GOOGLE
                ),
            )
        )

        identity_org = (
            Organization.objects.create(
                name=(
                    "F2 Google Workspace"
                ),
                slug=(
                    "f2-google-workspace"
                ),
                is_active=True,
            )
        )

        OrganizationUser.objects.create(
            user=identity_user,
            organization=identity_org,
            role="owner",
        )

        ExternalIdentity.objects.create(
            user=identity_user,
            provider=AUTH_METHOD_GOOGLE,
            issuer=(
                "https://accounts.google.com"
            ),
            subject=(
                "google-f2-subject"
            ),
            email_at_binding=(
                identity_user.email
            ),
        )

        grant = (
            create_identity_login_grant(
                user=identity_user,
                provider=(
                    AUTH_METHOD_GOOGLE
                ),
            )
        )

        token = self.seed_csrf()

        response = self.client.post(
            (
                "/api/auth/session/"
                "identity/exchange/"
            ),
            {
                "code":
                    grant,
            },
            format="json",
            HTTP_X_ONEUCH_CSRF=token,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertIn(
            "access",
            response.data,
        )

        self.assertNotIn(
            "refresh",
            response.data,
        )

        self.assertIn(
            BROWSER_REFRESH_COOKIE,
            response.cookies,
        )

        replay = self.client.post(
            (
                "/api/auth/session/"
                "identity/exchange/"
            ),
            {
                "code":
                    grant,
            },
            format="json",
            HTTP_X_ONEUCH_CSRF=token,
        )

        self.assertEqual(
            replay.status_code,
            401,
        )


    def test_legacy_password_jwt_endpoint_remains_available_during_f2(
        self,
    ):
        response = self.client.post(
            "/api/auth/token/",
            {
                "email":
                    self.user.email,

                "password":
                    self.PASSWORD,
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

        self.assertIn(
            "refresh",
            response.data,
        )
