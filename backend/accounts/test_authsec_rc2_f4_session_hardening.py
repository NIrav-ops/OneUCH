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
from rest_framework_simplejwt.settings import (
    api_settings,
)
from rest_framework_simplejwt.tokens import (
    AccessToken,
    RefreshToken,
)

from accounts.browser_session import (
    BROWSER_CSRF_COOKIE,
    BROWSER_REFRESH_COOKIE,
)
from accounts.identity_service import (
    create_identity_login_grant,
)
from accounts.models import (
    AUTH_METHOD_GOOGLE,
    AUTH_METHOD_WORK_EMAIL,
    BROWSER_SESSION_CLAIM,
    BrowserSession,
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
class AuthSecRC2F4SessionHardeningTests(
    TestCase,
):

    PASSWORD = (
        "OneUCH!F4Session93471"
    )


    def setUp(
        self,
    ):
        cache.clear()

        self.client = APIClient()

        self.user = (
            User.objects.create_user(
                email=(
                    "browser-f4@oneuch.test"
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
                    "F4 Browser Workspace"
                ),
                slug=(
                    "f4-browser-workspace"
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

        return response.data[
            "csrf_token"
        ]


    def login(
        self,
    ):
        csrf = self.seed_csrf()

        response = self.client.post(
            "/api/auth/session/login/",
            {
                "email":
                    self.user.email,

                "password":
                    self.PASSWORD,
            },
            format="json",
            HTTP_X_ONEUCH_CSRF=csrf,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        return (
            csrf,
            response,
        )


    def session_for_access(
        self,
        access,
    ):
        token = AccessToken(
            access
        )

        session_id = token[
            BROWSER_SESSION_CLAIM
        ]

        return (
            BrowserSession.objects.get(
                public_id=session_id
            )
        )


    def authenticated_me(
        self,
        access,
    ):
        client = APIClient()

        client.credentials(
            HTTP_AUTHORIZATION=(
                f"Bearer {access}"
            )
        )

        return client.get(
            "/api/auth/me/"
        )


    def test_csrf_seed_reuses_existing_cookie_across_tabs(
        self,
    ):
        first = self.client.get(
            "/api/auth/session/csrf/"
        )

        second = self.client.get(
            "/api/auth/session/csrf/"
        )

        self.assertEqual(
            first.status_code,
            200,
        )

        self.assertEqual(
            second.status_code,
            200,
        )

        self.assertEqual(
            first.data[
                "csrf_token"
            ],
            second.data[
                "csrf_token"
            ],
        )

        self.assertEqual(
            second.cookies[
                BROWSER_CSRF_COOKIE
            ].value,
            first.data[
                "csrf_token"
            ],
        )


    def test_password_login_creates_server_bound_browser_session(
        self,
    ):
        _csrf, response = (
            self.login()
        )

        access = response.data[
            "access"
        ]

        raw_refresh = (
            response.cookies[
                BROWSER_REFRESH_COOKIE
            ].value
        )

        session = (
            self.session_for_access(
                access
            )
        )

        refresh = RefreshToken(
            raw_refresh
        )

        self.assertEqual(
            str(
                refresh[
                    BROWSER_SESSION_CLAIM
                ]
            ),
            str(
                session.public_id
            ),
        )

        self.assertEqual(
            session.current_refresh_jti,
            str(
                refresh[
                    api_settings
                    .JTI_CLAIM
                ]
            ),
        )

        self.assertIsNone(
            session.revoked_at
        )

        self.assertEqual(
            self.authenticated_me(
                access
            ).status_code,
            200,
        )


    def test_refresh_rotates_cookie_and_keeps_session_active(
        self,
    ):
        csrf, login_response = (
            self.login()
        )

        old_refresh = (
            login_response.cookies[
                BROWSER_REFRESH_COOKIE
            ].value
        )

        session = (
            self.session_for_access(
                login_response.data[
                    "access"
                ]
            )
        )

        response = self.client.post(
            "/api/auth/session/refresh/",
            {},
            format="json",
            HTTP_X_ONEUCH_CSRF=csrf,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        new_refresh = (
            response.cookies[
                BROWSER_REFRESH_COOKIE
            ].value
        )

        self.assertNotEqual(
            new_refresh,
            old_refresh,
        )

        session.refresh_from_db()

        self.assertEqual(
            session.current_refresh_jti,
            str(
                RefreshToken(
                    new_refresh
                )[
                    api_settings
                    .JTI_CLAIM
                ]
            ),
        )

        self.assertIsNone(
            session.revoked_at
        )


    def test_refresh_reuse_revokes_session_and_rejects_bound_access(
        self,
    ):
        csrf, login_response = (
            self.login()
        )

        old_refresh = (
            login_response.cookies[
                BROWSER_REFRESH_COOKIE
            ].value
        )

        first_refresh = self.client.post(
            "/api/auth/session/refresh/",
            {},
            format="json",
            HTTP_X_ONEUCH_CSRF=csrf,
        )

        self.assertEqual(
            first_refresh.status_code,
            200,
        )

        rotated_access = (
            first_refresh.data[
                "access"
            ]
        )

        session = (
            self.session_for_access(
                rotated_access
            )
        )

        self.client.cookies[
            BROWSER_REFRESH_COOKIE
        ] = old_refresh

        replay = self.client.post(
            "/api/auth/session/refresh/",
            {},
            format="json",
            HTTP_X_ONEUCH_CSRF=csrf,
        )

        self.assertEqual(
            replay.status_code,
            401,
        )

        session.refresh_from_db()

        self.assertIsNotNone(
            session.revoked_at
        )

        self.assertEqual(
            session.revocation_reason,
            "refresh_reuse",
        )

        self.assertEqual(
            self.authenticated_me(
                rotated_access
            ).status_code,
            401,
        )


    def test_bootstrap_rotates_refresh_cookie(
        self,
    ):
        csrf, login_response = (
            self.login()
        )

        old_refresh = (
            login_response.cookies[
                BROWSER_REFRESH_COOKIE
            ].value
        )

        response = self.client.post(
            "/api/auth/session/bootstrap/",
            {},
            format="json",
            HTTP_X_ONEUCH_CSRF=csrf,
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

        self.assertNotEqual(
            response.cookies[
                BROWSER_REFRESH_COOKIE
            ].value,
            old_refresh,
        )


    def test_session_end_revokes_server_session_and_bound_access(
        self,
    ):
        csrf, login_response = (
            self.login()
        )

        access = login_response.data[
            "access"
        ]

        session = (
            self.session_for_access(
                access
            )
        )

        response = self.client.post(
            "/api/auth/session/end/",
            {},
            format="json",
            HTTP_X_ONEUCH_CSRF=csrf,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        session.refresh_from_db()

        self.assertIsNotNone(
            session.revoked_at
        )

        self.assertEqual(
            session.revocation_reason,
            "logout",
        )

        self.assertEqual(
            self.authenticated_me(
                access
            ).status_code,
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

        self.assertEqual(
            response.cookies[
                BROWSER_CSRF_COOKIE
            ][
                "max-age"
            ],
            0,
        )


    def test_identity_exchange_creates_server_bound_browser_session(
        self,
    ):
        identity_user = (
            User.objects.create_user(
                email=(
                    "google-f4@oneuch.test"
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
                    "F4 Google Workspace"
                ),
                slug=(
                    "f4-google-workspace"
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
                "google-f4-subject"
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

        csrf = self.seed_csrf()

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
            HTTP_X_ONEUCH_CSRF=csrf,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotIn(
            "refresh",
            response.data,
        )

        session = (
            self.session_for_access(
                response.data[
                    "access"
                ]
            )
        )

        self.assertEqual(
            session.user_id,
            identity_user.id,
        )

        self.assertIsNone(
            session.revoked_at
        )


    def test_legacy_jwt_without_browser_session_claim_remains_compatible(
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

        access = response.data[
            "access"
        ]

        self.assertNotIn(
            BROWSER_SESSION_CLAIM,
            AccessToken(
                access
            ).payload,
        )

        self.assertEqual(
            self.authenticated_me(
                access
            ).status_code,
            200,
        )
