from unittest.mock import (
    patch,
)

from urllib.parse import (
    parse_qs,
    unquote,
    urlsplit,
)

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

from accounts.identity_service import (
    IDENTITY_REGISTRATION_CONTEXT_COOKIE,
    IdentityClaims,
)

from accounts.models import (
    AUTH_METHOD_GOOGLE,
    AUTH_METHOD_MICROSOFT,
    ExternalIdentity,
    IdentityLoginGrant,
    RegistrationRequest,
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
    AUTH_GOVERNED_REGISTRATION_ENABLED=True,
    AUTH_IDENTITY_STATE_MAX_AGE_SECONDS=600,
    AUTH_IDENTITY_GRANT_LIFETIME_SECONDS=120,
    AUTH_IDENTITY_PROVIDER_TIMEOUT_SECONDS=10,
    ONEUCH_FRONTEND_LOGIN_URL=(
        "http://localhost:5173/login"
    ),
    ONEUCH_PRIVACY_NOTICE_VERSION=(
        "privacy-2026-09"
    ),
    ONEUCH_TERMS_VERSION=(
        "terms-2026-09"
    ),
    ONEUCH_REGION=(
        "ap-south-1"
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
class H2B3D3BFederatedRegistrationTests(
    TestCase,
):

    def setUp(
        self,
    ):
        cache.clear()

        self.client = (
            APIClient()
        )


    def registration_start(
        self,
        provider,
        *,
        organization_name=(
            "D3B Federated Company"
        ),
        acknowledged=True,
    ):
        return self.client.post(
            (
                "/api/auth/identity/"
                "registration/"
                + provider
                + "/start/"
            ),
            {
                "organization_name":
                    organization_name,

                "acknowledged":
                    acknowledged,
            },
            format="json",
        )


    def state_from_start(
        self,
        response,
    ):
        authorization_url = (
            response.data[
                "authorization_url"
            ]
        )

        parsed = urlsplit(
            authorization_url
        )

        query = parse_qs(
            parsed.query
        )

        return (
            authorization_url,
            query[
                "state"
            ][
                0
            ],
        )


    def callback(
        self,
        *,
        provider,
        claims,
        start_response=None,
    ):
        start_response = (
            start_response
            or
            self.registration_start(
                provider
            )
        )

        (
            _,
            state,
        ) = self.state_from_start(
            start_response
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
                        "synthetic-registration-code",

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


    def google_claims(
        self,
        *,
        email=(
            "google-d3b@oneuch.test"
        ),
        subject=(
            "google-d3b-subject"
        ),
    ):
        return IdentityClaims(
            provider=(
                AUTH_METHOD_GOOGLE
            ),
            issuer=(
                "https://accounts.google.com"
            ),
            subject=subject,
            email=email,
        )


    def microsoft_claims(
        self,
        *,
        email=(
            "microsoft-d3b@oneuch.test"
        ),
        subject=(
            "microsoft-d3b-subject"
        ),
    ):
        return IdentityClaims(
            provider=(
                AUTH_METHOD_MICROSOFT
            ),
            issuer=(
                "https://login.microsoftonline.com/"
                "tenant-d3b/v2.0"
            ),
            subject=subject,
            email=email,
        )


    def test_registration_config_exposes_only_safe_server_policy(
        self,
    ):
        response = (
            self.client.get(
                (
                    "/api/auth/identity/"
                    "registration/config/"
                )
            )
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

                "privacy_notice_version":
                    "privacy-2026-09",

                "terms_version":
                    "terms-2026-09",
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

        self.assertNotIn(
            "ap-south-1",
            serialized,
        )


    @override_settings(
        AUTH_GOVERNED_REGISTRATION_ENABLED=False
    )
    def test_registration_feature_fails_closed_when_disabled(
        self,
    ):
        config = (
            self.client.get(
                (
                    "/api/auth/identity/"
                    "registration/config/"
                )
            )
        )


        self.assertEqual(
            config.status_code,
            200,
        )

        self.assertEqual(
            config.data,
            {
                "enabled":
                    False,

                "providers":
                    [],
            },
        )


        start = (
            self.registration_start(
                AUTH_METHOD_GOOGLE
            )
        )


        self.assertEqual(
            start.status_code,
            404,
        )


    def test_registration_start_requires_explicit_acknowledgement(
        self,
    ):
        response = (
            self.registration_start(
                AUTH_METHOD_GOOGLE,
                acknowledged=False,
            )
        )


        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertNotIn(
            IDENTITY_REGISTRATION_CONTEXT_COOKIE,
            response.cookies,
        )

        self.assertEqual(
            RegistrationRequest.objects.count(),
            0,
        )


    def test_registration_start_keeps_business_context_out_of_idp_state(
        self,
    ):
        organization_name = (
            "Highly Confidential Customer Workspace"
        )


        response = (
            self.registration_start(
                AUTH_METHOD_GOOGLE,
                organization_name=(
                    organization_name
                ),
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        self.assertIn(
            IDENTITY_REGISTRATION_CONTEXT_COOKIE,
            response.cookies,
        )


        cookie = (
            response.cookies[
                IDENTITY_REGISTRATION_CONTEXT_COOKIE
            ]
        )


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


        authorization_url = (
            response.data[
                "authorization_url"
            ]
        )


        decoded_url = (
            unquote(
                authorization_url
            )
        )


        self.assertNotIn(
            organization_name,
            decoded_url,
        )

        self.assertNotIn(
            "privacy-2026-09",
            decoded_url,
        )

        self.assertNotIn(
            "terms-2026-09",
            decoded_url,
        )

        self.assertNotIn(
            "ap-south-1",
            decoded_url,
        )


        query = parse_qs(
            urlsplit(
                authorization_url
            ).query
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
            "state",
            query,
        )

        self.assertIn(
            "nonce",
            query,
        )

        self.assertNotIn(
            "gmail",
            authorization_url.lower(),
        )

        self.assertNotIn(
            "mail.read",
            authorization_url.lower(),
        )

        self.assertNotIn(
            "mail.send",
            authorization_url.lower(),
        )


        self.assertEqual(
            RegistrationRequest.objects.count(),
            0,
        )

        self.assertEqual(
            User.objects.count(),
            0,
        )


    def test_google_registration_callback_creates_pending_fail_closed_registration(
        self,
    ):
        callback = (
            self.callback(
                provider=(
                    AUTH_METHOD_GOOGLE
                ),
                claims=(
                    self.google_claims()
                ),
            )
        )


        self.assertEqual(
            callback.status_code,
            302,
        )


        query = (
            self.redirect_query(
                callback
            )
        )


        self.assertEqual(
            query[
                "registration_status"
            ][
                0
            ],
            "pending",
        )

        self.assertEqual(
            query[
                "registration_created"
            ][
                0
            ],
            "1",
        )

        self.assertEqual(
            query[
                "identity_provider"
            ][
                0
            ],
            "google",
        )


        registration = (
            RegistrationRequest.objects
            .select_related(
                "user",
                "organization",
            )
            .get()
        )


        self.assertEqual(
            query[
                "registration_id"
            ][
                0
            ],
            registration.public_id,
        )


        self.assertFalse(
            registration.user.is_active
        )

        self.assertFalse(
            registration.organization.is_active
        )

        self.assertFalse(
            registration.user.has_usable_password()
        )


        membership = (
            OrganizationUser.objects
            .get(
                user=(
                    registration.user
                )
            )
        )


        self.assertEqual(
            membership.role,
            "owner",
        )


        self.assertTrue(
            ExternalIdentity.objects
            .filter(
                user=(
                    registration.user
                ),
                provider=(
                    AUTH_METHOD_GOOGLE
                ),
            )
            .exists()
        )


        self.assertEqual(
            IdentityLoginGrant.objects.count(),
            0,
        )

        self.assertEqual(
            OAuthToken.objects.count(),
            0,
        )

        self.assertEqual(
            EmailAccount.objects.count(),
            0,
        )


        audit = (
            AuditLog.objects
            .get(
                action=(
                    "REGISTRATION_REQUESTED"
                )
            )
        )


        self.assertEqual(
            audit.organization,
            registration.organization,
        )


        self.assertIn(
            IDENTITY_REGISTRATION_CONTEXT_COOKIE,
            callback.cookies,
        )


        self.assertEqual(
            callback.cookies[
                IDENTITY_REGISTRATION_CONTEXT_COOKIE
            ][
                "max-age"
            ],
            0,
        )


    def test_microsoft_registration_callback_creates_pending_registration(
        self,
    ):
        callback = (
            self.callback(
                provider=(
                    AUTH_METHOD_MICROSOFT
                ),
                claims=(
                    self.microsoft_claims()
                ),
            )
        )


        query = (
            self.redirect_query(
                callback
            )
        )


        self.assertEqual(
            query[
                "registration_status"
            ][
                0
            ],
            "pending",
        )


        registration = (
            RegistrationRequest.objects
            .get()
        )


        self.assertEqual(
            registration.provider,
            AUTH_METHOD_MICROSOFT,
        )

        self.assertFalse(
            registration.user.is_active
        )

        self.assertFalse(
            registration.organization.is_active
        )

        self.assertEqual(
            IdentityLoginGrant.objects.count(),
            0,
        )

        self.assertEqual(
            OAuthToken.objects.count(),
            0,
        )

        self.assertEqual(
            EmailAccount.objects.count(),
            0,
        )


    def test_tampered_registration_context_fails_without_provisioning(
        self,
    ):
        start = (
            self.registration_start(
                AUTH_METHOD_GOOGLE
            )
        )


        (
            _,
            state,
        ) = self.state_from_start(
            start
        )


        self.client.cookies[
            IDENTITY_REGISTRATION_CONTEXT_COOKIE
        ] = (
            "tampered-registration-context"
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

            response = (
                self.client.get(
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
            )


        query = (
            self.redirect_query(
                response
            )
        )


        self.assertEqual(
            query[
                "registration_error"
            ][
                0
            ],
            "registration_failed",
        )

        self.assertEqual(
            User.objects.count(),
            0,
        )

        self.assertEqual(
            Organization.objects.count(),
            0,
        )

        self.assertEqual(
            ExternalIdentity.objects.count(),
            0,
        )

        self.assertEqual(
            RegistrationRequest.objects.count(),
            0,
        )


    def test_existing_email_collision_is_not_auto_linked(
        self,
    ):
        existing = (
            User.objects
            .create_user(
                email=(
                    "collision-d3b@oneuch.test"
                ),
                password=(
                    "OneUCH!CollisionD3B93471"
                ),
            )
        )


        callback = (
            self.callback(
                provider=(
                    AUTH_METHOD_GOOGLE
                ),
                claims=(
                    self.google_claims(
                        email=(
                            existing.email
                        ),
                        subject=(
                            "collision-d3b-subject"
                        ),
                    )
                ),
            )
        )


        query = (
            self.redirect_query(
                callback
            )
        )


        self.assertEqual(
            query[
                "registration_error"
            ][
                0
            ],
            "registration_failed",
        )


        self.assertFalse(
            ExternalIdentity.objects
            .filter(
                user=existing
            )
            .exists()
        )

        self.assertEqual(
            RegistrationRequest.objects.count(),
            0,
        )


    def test_exact_registration_replay_is_idempotent(
        self,
    ):
        first = (
            self.callback(
                provider=(
                    AUTH_METHOD_GOOGLE
                ),
                claims=(
                    self.google_claims(
                        email=(
                            "replay-d3b@oneuch.test"
                        ),
                        subject=(
                            "replay-d3b-subject"
                        ),
                    )
                ),
            )
        )


        first_query = (
            self.redirect_query(
                first
            )
        )


        self.assertEqual(
            first_query[
                "registration_created"
            ][
                0
            ],
            "1",
        )


        counts = {
            "users":
                User.objects.count(),

            "organizations":
                Organization.objects.count(),

            "memberships":
                OrganizationUser.objects.count(),

            "identities":
                ExternalIdentity.objects.count(),

            "registrations":
                RegistrationRequest.objects.count(),
        }


        second_start = (
            self.registration_start(
                AUTH_METHOD_GOOGLE
            )
        )


        second = (
            self.callback(
                provider=(
                    AUTH_METHOD_GOOGLE
                ),
                claims=(
                    self.google_claims(
                        email=(
                            "replay-d3b@oneuch.test"
                        ),
                        subject=(
                            "replay-d3b-subject"
                        ),
                    )
                ),
                start_response=(
                    second_start
                ),
            )
        )


        second_query = (
            self.redirect_query(
                second
            )
        )


        self.assertEqual(
            second_query[
                "registration_created"
            ][
                0
            ],
            "0",
        )

        self.assertEqual(
            User.objects.count(),
            counts["users"],
        )

        self.assertEqual(
            Organization.objects.count(),
            counts["organizations"],
        )

        self.assertEqual(
            OrganizationUser.objects.count(),
            counts["memberships"],
        )

        self.assertEqual(
            ExternalIdentity.objects.count(),
            counts["identities"],
        )

        self.assertEqual(
            RegistrationRequest.objects.count(),
            counts["registrations"],
        )

        self.assertEqual(
            IdentityLoginGrant.objects.count(),
            0,
        )
