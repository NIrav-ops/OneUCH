
from datetime import (
    timedelta,
)
from unittest.mock import (
    patch,
)
from urllib.parse import (
    parse_qs,
    urlsplit,
)

from django.core.cache import (
    cache,
)

from django.test import (
    TestCase,
    override_settings,
)
from django.utils import (
    timezone,
)

from rest_framework.test import (
    APIClient,
)

from accounts.identity_service import (
    IDENTITY_BROWSER_BINDING_COOKIE,
    IdentityAuthenticationError,
    IdentityClaims,
    build_authorization_url,
    create_identity_login_grant,
    validate_google_claims,
    validate_microsoft_claims,
)
from accounts.models import (
    AUTH_METHOD_GOOGLE,
    AUTH_METHOD_MICROSOFT,
    AUTH_METHOD_WORK_EMAIL,
    ExternalIdentity,
    IdentityLoginGrant,
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
from oauth_tokens.models import (
    OAuthToken,
)


@override_settings(
    AUTH_IDENTITY_SIGNIN_ENABLED=True,
    AUTH_IDENTITY_STATE_MAX_AGE_SECONDS=600,
    AUTH_IDENTITY_GRANT_LIFETIME_SECONDS=120,
    AUTH_IDENTITY_PROVIDER_TIMEOUT_SECONDS=10,
    ONEUCH_FRONTEND_LOGIN_URL=(
        "http://localhost:5173/login"
    ),
    GOOGLE_IDENTITY_CLIENT_ID=(
        "synthetic-google-identity-client"
    ),
    GOOGLE_IDENTITY_CLIENT_SECRET=(
        "synthetic-google-identity-secret"
    ),
    GOOGLE_IDENTITY_REDIRECT_URI=(
        "http://127.0.0.1:8000/"
        "api/auth/identity/google/callback/"
    ),
    MICROSOFT_IDENTITY_CLIENT_ID=(
        "synthetic-microsoft-identity-client"
    ),
    MICROSOFT_IDENTITY_CLIENT_SECRET=(
        "synthetic-microsoft-identity-secret"
    ),
    MICROSOFT_IDENTITY_TENANT_ID=(
        "organizations"
    ),
    MICROSOFT_IDENTITY_REDIRECT_URI=(
        "http://127.0.0.1:8000/"
        "api/auth/identity/microsoft/callback/"
    ),
)
class AuthRC1BE2IdentityTests(
    TestCase,
):

    PASSWORD = (
        "OneUCH!E2Identity93471"
    )

    def setUp(
        self,
    ):
        # Isolate ScopedRateThrottle cache state between
        # test methods. Production rate limits remain
        # unchanged.
        cache.clear()

        self.client = APIClient()

        self.google_user = (
            self.create_identity_user(
                email=(
                    "google-e2@oneuch.test"
                ),
                provider=(
                    AUTH_METHOD_GOOGLE
                ),
            )
        )

        self.microsoft_user = (
            self.create_identity_user(
                email=(
                    "microsoft-e2@oneuch.test"
                ),
                provider=(
                    AUTH_METHOD_MICROSOFT
                ),
            )
        )

    def create_identity_user(
        self,
        *,
        email,
        provider,
        active=True,
        workspace=True,
        workspace_active=True,
    ):
        user = (
            User.objects
            .create_user(
                email=email,
                password=self.PASSWORD,
                signup_method=provider,
                is_active=active,
            )
        )

        if workspace:
            organization = (
                Organization.objects
                .create(
                    name=(
                        "E2 Identity Workspace"
                    ),
                    slug=(
                        "e2-"
                        + str(
                            user.id
                        )
                        + "-"
                        + provider
                    ),
                    is_active=(
                        workspace_active
                    ),
                )
            )

            OrganizationUser.objects.create(
                user=user,
                organization=organization,
                role="owner",
            )

        return user

    def google_claims(
        self,
        *,
        email=None,
        subject="google-subject-e2",
    ):
        return IdentityClaims(
            provider=(
                AUTH_METHOD_GOOGLE
            ),
            issuer=(
                "https://accounts.google.com"
            ),
            subject=subject,
            email=(
                email
                or
                self.google_user.email
            ),
        )

    def microsoft_claims(
        self,
        *,
        email=None,
        subject="microsoft-subject-e2",
    ):
        return IdentityClaims(
            provider=(
                AUTH_METHOD_MICROSOFT
            ),
            issuer=(
                "https://login.microsoftonline.com/"
                "tenant-e2/v2.0"
            ),
            subject=subject,
            email=(
                email
                or
                self.microsoft_user.email
            ),
        )

    def state_for(
        self,
        provider,
    ):
        response = self.client.get(
            (
                "/api/auth/identity/"
                + provider
                + "/start/"
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertIn(
            IDENTITY_BROWSER_BINDING_COOKIE,
            response.cookies,
        )

        query = parse_qs(
            urlsplit(
                response[
                    "Location"
                ]
            ).query
        )

        return (
            query[
                "state"
            ][
                0
            ]
        )

    def callback(
        self,
        *,
        provider,
        claims,
    ):
        state = (
            self.state_for(
                provider
            )
        )

        with patch(
            (
                "accounts.identity_views."
                "exchange_identity_code"
            ),
            return_value=claims,
        ):

            return self.client.get(
                (
                    "/api/auth/identity/"
                    + provider
                    + "/callback/"
                ),
                {
                    "code":
                        "synthetic-code",

                    "state":
                        state,
                },
            )

    def redirect_query(
        self,
        response,
    ):
        return parse_qs(
            urlsplit(
                response[
                    "Location"
                ]
            ).query
        )

    def test_provider_status_lists_configured_identity_providers(
        self,
    ):
        response = self.client.get(
            "/api/auth/identity/providers/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data,
            {
                "enabled":
                    True,

                "providers": [
                    "google",
                    "microsoft",
                ],
            },
        )

        serialized = str(
            response.data
        ).lower()

        self.assertNotIn(
            "client_secret",
            serialized,
        )

        self.assertNotIn(
            "client_id",
            serialized,
        )

    def test_google_start_uses_identity_only_oidc_scopes(
        self,
    ):
        response = self.client.get(
            "/api/auth/identity/google/start/"
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        url = response[
            "Location"
        ]

        cookie = response.cookies[
            IDENTITY_BROWSER_BINDING_COOKIE
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
            "/api/auth/identity/",
        )

        parsed = urlsplit(
            url
        )

        query = parse_qs(
            parsed.query
        )

        self.assertEqual(
            parsed.netloc,
            "accounts.google.com",
        )

        self.assertEqual(
            set(
                query[
                    "scope"
                ][
                    0
                ].split()
            ),
            {
                "openid",
                "email",
                "profile",
            },
        )

        self.assertIn(
            "nonce",
            query,
        )

        self.assertIn(
            "state",
            query,
        )

        self.assertEqual(
            query[
                "redirect_uri"
            ][
                0
            ],
            (
                "http://127.0.0.1:8000/"
                "api/auth/identity/google/callback/"
            ),
        )

        self.assertNotIn(
            "gmail",
            url.lower(),
        )

    def test_microsoft_start_uses_identity_only_oidc_scopes(
        self,
    ):
        response = self.client.get(
            "/api/auth/identity/microsoft/start/"
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        url = response[
            "Location"
        ]

        cookie = response.cookies[
            IDENTITY_BROWSER_BINDING_COOKIE
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
            "/api/auth/identity/",
        )

        parsed = urlsplit(
            url
        )

        query = parse_qs(
            parsed.query
        )

        self.assertEqual(
            parsed.netloc,
            "login.microsoftonline.com",
        )

        self.assertEqual(
            set(
                query[
                    "scope"
                ][
                    0
                ].split()
            ),
            {
                "openid",
                "email",
                "profile",
            },
        )

        self.assertNotIn(
            "Mail.ReadWrite",
            url,
        )

        self.assertNotIn(
            "Mail.Send",
            url,
        )

        self.assertEqual(
            query[
                "redirect_uri"
            ][
                0
            ],
            (
                "http://127.0.0.1:8000/"
                "api/auth/identity/microsoft/callback/"
            ),
        )

    @override_settings(
        AUTH_IDENTITY_SIGNIN_ENABLED=False
    )
    def test_identity_feature_fails_closed_when_disabled(
        self,
    ):
        providers = self.client.get(
            "/api/auth/identity/providers/"
        )

        self.assertEqual(
            providers.status_code,
            200,
        )

        self.assertEqual(
            providers.data,
            {
                "enabled":
                    False,

                "providers":
                    [],
            },
        )

        start = self.client.get(
            "/api/auth/identity/google/start/"
        )

        self.assertEqual(
            start.status_code,
            404,
        )

        exchange = self.client.post(
            "/api/auth/identity/exchange/",
            {
                "code":
                    "synthetic",
            },
            format="json",
        )

        self.assertEqual(
            exchange.status_code,
            404,
        )

    def test_google_callback_binds_controlled_user_without_mailbox_side_effects(
        self,
    ):
        response = self.callback(
            provider=(
                AUTH_METHOD_GOOGLE
            ),
            claims=(
                self.google_claims()
            ),
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        query = (
            self.redirect_query(
                response
            )
        )

        self.assertIn(
            "identity_code",
            query,
        )

        self.assertEqual(
            query[
                "identity_provider"
            ][
                0
            ],
            "google",
        )

        binding = (
            ExternalIdentity.objects.get(
                user=self.google_user,
                provider="google",
            )
        )

        self.assertEqual(
            binding.subject,
            "google-subject-e2",
        )

        self.assertEqual(
            OAuthToken.objects.count(),
            0,
        )

        self.assertEqual(
            EmailAccount.objects.count(),
            0,
        )

    def test_microsoft_callback_binds_controlled_user_without_mailbox_side_effects(
        self,
    ):
        response = self.callback(
            provider=(
                AUTH_METHOD_MICROSOFT
            ),
            claims=(
                self.microsoft_claims()
            ),
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        query = (
            self.redirect_query(
                response
            )
        )

        self.assertIn(
            "identity_code",
            query,
        )

        self.assertEqual(
            query[
                "identity_provider"
            ][
                0
            ],
            "microsoft",
        )

        binding = (
            ExternalIdentity.objects.get(
                user=self.microsoft_user,
                provider="microsoft",
            )
        )

        self.assertEqual(
            binding.subject,
            "microsoft-subject-e2",
        )

        self.assertEqual(
            OAuthToken.objects.count(),
            0,
        )

        self.assertEqual(
            EmailAccount.objects.count(),
            0,
        )

    def test_work_email_account_is_not_auto_linked_by_matching_email(
        self,
    ):
        work_user = (
            User.objects
            .create_user(
                email=(
                    "work-collision@oneuch.test"
                ),
                password=self.PASSWORD,
                signup_method=(
                    AUTH_METHOD_WORK_EMAIL
                ),
            )
        )

        organization = (
            Organization.objects
            .create(
                name="Work Collision",
                slug="work-collision",
            )
        )

        OrganizationUser.objects.create(
            user=work_user,
            organization=organization,
            role="owner",
        )

        response = self.callback(
            provider=(
                AUTH_METHOD_GOOGLE
            ),
            claims=(
                self.google_claims(
                    email=work_user.email,
                    subject=(
                        "collision-google-sub"
                    ),
                )
            ),
        )

        query = (
            self.redirect_query(
                response
            )
        )

        self.assertEqual(
            query[
                "identity_error"
            ][
                0
            ],
            "signin_failed",
        )

        self.assertFalse(
            ExternalIdentity.objects
            .filter(
                user=work_user
            )
            .exists()
        )

    def test_unknown_provider_identity_is_not_auto_provisioned(
        self,
    ):
        before = (
            User.objects.count()
        )

        response = self.callback(
            provider=(
                AUTH_METHOD_GOOGLE
            ),
            claims=(
                self.google_claims(
                    email=(
                        "unknown-e2@oneuch.test"
                    ),
                    subject=(
                        "unknown-subject-e2"
                    ),
                )
            ),
        )

        query = (
            self.redirect_query(
                response
            )
        )

        self.assertEqual(
            query[
                "identity_error"
            ][
                0
            ],
            "signin_failed",
        )

        self.assertEqual(
            User.objects.count(),
            before,
        )

    def test_inactive_workspace_identity_is_rejected(
        self,
    ):
        user = (
            self.create_identity_user(
                email=(
                    "inactive-google@oneuch.test"
                ),
                provider=(
                    AUTH_METHOD_GOOGLE
                ),
                workspace_active=False,
            )
        )

        response = self.callback(
            provider=(
                AUTH_METHOD_GOOGLE
            ),
            claims=(
                self.google_claims(
                    email=user.email,
                    subject=(
                        "inactive-subject"
                    ),
                )
            ),
        )

        query = (
            self.redirect_query(
                response
            )
        )

        self.assertEqual(
            query[
                "identity_error"
            ][
                0
            ],
            "signin_failed",
        )

        self.assertFalse(
            ExternalIdentity.objects
            .filter(
                user=user
            )
            .exists()
        )

    def test_existing_provider_binding_cannot_switch_subject(
        self,
    ):
        ExternalIdentity.objects.create(
            user=self.google_user,
            provider=(
                AUTH_METHOD_GOOGLE
            ),
            issuer=(
                "https://accounts.google.com"
            ),
            subject="original-subject",
            email_at_binding=(
                self.google_user.email
            ),
        )

        response = self.callback(
            provider=(
                AUTH_METHOD_GOOGLE
            ),
            claims=(
                self.google_claims(
                    subject="attacker-subject"
                )
            ),
        )

        query = (
            self.redirect_query(
                response
            )
        )

        self.assertEqual(
            query[
                "identity_error"
            ][
                0
            ],
            "signin_failed",
        )

        self.assertEqual(
            ExternalIdentity.objects
            .filter(
                user=self.google_user,
                provider="google",
            )
            .count(),
            1,
        )

    def test_bound_subject_cannot_switch_oneuch_email(
        self,
    ):
        ExternalIdentity.objects.create(
            user=self.google_user,
            provider=(
                AUTH_METHOD_GOOGLE
            ),
            issuer=(
                "https://accounts.google.com"
            ),
            subject="stable-subject",
            email_at_binding=(
                self.google_user.email
            ),
        )

        response = self.callback(
            provider=(
                AUTH_METHOD_GOOGLE
            ),
            claims=(
                self.google_claims(
                    email=(
                        "different-email@oneuch.test"
                    ),
                    subject="stable-subject",
                )
            ),
        )

        query = (
            self.redirect_query(
                response
            )
        )

        self.assertEqual(
            query[
                "identity_error"
            ][
                0
            ],
            "signin_failed",
        )

    def test_callback_rejects_valid_state_without_browser_binding_cookie(
        self,
    ):
        state = self.state_for(
            AUTH_METHOD_GOOGLE
        )

        self.client.cookies.pop(
            IDENTITY_BROWSER_BINDING_COOKIE,
            None,
        )

        with patch(
            (
                "accounts.identity_views."
                "exchange_identity_code"
            ),
            return_value=(
                self.google_claims()
            ),
        ):
            response = self.client.get(
                (
                    "/api/auth/identity/"
                    "google/callback/"
                ),
                {
                    "code":
                        "synthetic-code",

                    "state":
                        state,
                },
            )

        query = (
            self.redirect_query(
                response
            )
        )

        self.assertEqual(
            query[
                "identity_error"
            ][
                0
            ],
            "signin_failed",
        )

        self.assertEqual(
            ExternalIdentity.objects.count(),
            0,
        )

        self.assertEqual(
            IdentityLoginGrant.objects.count(),
            0,
        )


    def test_callback_rejects_mismatched_browser_binding_cookie(
        self,
    ):
        state = self.state_for(
            AUTH_METHOD_GOOGLE
        )

        self.client.cookies[
            IDENTITY_BROWSER_BINDING_COOKIE
        ] = (
            "mismatched-browser-binding"
        )

        with patch(
            (
                "accounts.identity_views."
                "exchange_identity_code"
            ),
            return_value=(
                self.google_claims()
            ),
        ):
            response = self.client.get(
                (
                    "/api/auth/identity/"
                    "google/callback/"
                ),
                {
                    "code":
                        "synthetic-code",

                    "state":
                        state,
                },
            )

        query = (
            self.redirect_query(
                response
            )
        )

        self.assertEqual(
            query[
                "identity_error"
            ][
                0
            ],
            "signin_failed",
        )

        self.assertEqual(
            ExternalIdentity.objects.count(),
            0,
        )

        self.assertEqual(
            IdentityLoginGrant.objects.count(),
            0,
        )


    def test_successful_callback_clears_browser_binding_cookie(
        self,
    ):
        response = self.callback(
            provider=(
                AUTH_METHOD_GOOGLE
            ),
            claims=(
                self.google_claims()
            ),
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertIn(
            IDENTITY_BROWSER_BINDING_COOKIE,
            response.cookies,
        )

        cleared = response.cookies[
            IDENTITY_BROWSER_BINDING_COOKIE
        ]

        self.assertEqual(
            cleared[
                "max-age"
            ],
            0,
        )


    def test_login_grant_returns_oneuch_jwt_exactly_once_and_audits_method(
        self,
    ):
        callback = self.callback(
            provider=(
                AUTH_METHOD_GOOGLE
            ),
            claims=(
                self.google_claims()
            ),
        )

        code = (
            self.redirect_query(
                callback
            )[
                "identity_code"
            ][
                0
            ]
        )

        response = self.client.post(
            "/api/auth/identity/exchange/",
            {
                "code":
                    code,
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

        self.google_user.refresh_from_db()

        self.assertEqual(
            self.google_user.last_auth_method,
            AUTH_METHOD_GOOGLE,
        )

        audit = (
            AuditLog.objects
            .filter(
                user=self.google_user,
                action="LOGIN",
            )
            .latest(
                "id"
            )
        )

        self.assertEqual(
            audit.metadata[
                "auth_method"
            ],
            AUTH_METHOD_GOOGLE,
        )

        grant = (
            IdentityLoginGrant.objects.get(
                user=self.google_user,
                provider=(
                    AUTH_METHOD_GOOGLE
                ),
            )
        )

        self.assertIsNotNone(
            grant.used_at
        )

        replay = self.client.post(
            "/api/auth/identity/exchange/",
            {
                "code":
                    code,
            },
            format="json",
        )

        self.assertEqual(
            replay.status_code,
            401,
        )

        self.assertEqual(
            OAuthToken.objects.count(),
            0,
        )

        self.assertEqual(
            EmailAccount.objects.count(),
            0,
        )

    def test_expired_login_grant_is_rejected(
        self,
    ):
        ExternalIdentity.objects.create(
            user=self.google_user,
            provider=(
                AUTH_METHOD_GOOGLE
            ),
            issuer=(
                "https://accounts.google.com"
            ),
            subject="expired-grant-subject",
            email_at_binding=(
                self.google_user.email
            ),
        )

        raw_grant = (
            create_identity_login_grant(
                user=self.google_user,
                provider=(
                    AUTH_METHOD_GOOGLE
                ),
            )
        )

        IdentityLoginGrant.objects.filter(
            user=self.google_user
        ).update(
            expires_at=(
                timezone.now()
                -
                timedelta(
                    seconds=1
                )
            )
        )

        response = self.client.post(
            "/api/auth/identity/exchange/",
            {
                "code":
                    raw_grant,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_google_unverified_email_is_rejected(
        self,
    ):
        with self.assertRaises(
            IdentityAuthenticationError
        ):
            validate_google_claims(
                {
                    "iss":
                        "https://accounts.google.com",

                    "sub":
                        "google-unverified",

                    "email":
                        "google-e2@oneuch.test",

                    "email_verified":
                        False,

                    "nonce":
                        "expected",
                },
                expected_nonce=(
                    "expected"
                ),
            )

    def test_provider_nonce_mismatch_is_rejected(
        self,
    ):
        with self.assertRaises(
            IdentityAuthenticationError
        ):
            validate_google_claims(
                {
                    "iss":
                        "https://accounts.google.com",

                    "sub":
                        "google-nonce",

                    "email":
                        "google-e2@oneuch.test",

                    "email_verified":
                        True,

                    "nonce":
                        "wrong",
                },
                expected_nonce=(
                    "expected"
                ),
            )

        with self.assertRaises(
            IdentityAuthenticationError
        ):
            validate_microsoft_claims(
                {
                    "iss": (
                        "https://login.microsoftonline.com/"
                        "tenant-e2/v2.0"
                    ),

                    "tid":
                        "tenant-e2",

                    "sub":
                        "microsoft-nonce",

                    "preferred_username":
                        "microsoft-e2@oneuch.test",

                    "nonce":
                        "wrong",
                },
                expected_nonce=(
                    "expected"
                ),
            )
