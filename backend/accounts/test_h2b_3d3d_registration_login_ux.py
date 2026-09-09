from unittest.mock import patch

from urllib.parse import (
    parse_qs,
    urlsplit,
)

from django.test import (
    TestCase,
    override_settings,
)

from django.utils import timezone

from rest_framework.test import (
    APIClient,
)

from accounts.identity_service import (
    IdentityClaims,
)

from accounts.models import (
    AUTH_METHOD_GOOGLE,
    REGISTRATION_STATUS_PENDING,
    REGISTRATION_STATUS_REJECTED,
    User,
)

from accounts.registration_service import (
    registration_review_state_for_verified_identity,
    reject_registration_request,
    submit_registration_request,
)


@override_settings(
    AUTH_IDENTITY_SIGNIN_ENABLED=True,
    AUTH_GOVERNED_REGISTRATION_ENABLED=True,
    AUTH_IDENTITY_STATE_MAX_AGE_SECONDS=600,
    AUTH_IDENTITY_GRANT_LIFETIME_SECONDS=120,
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
        "synthetic-google-client"
    ),
    GOOGLE_IDENTITY_CLIENT_SECRET=(
        "synthetic-google-secret"
    ),
    GOOGLE_IDENTITY_REDIRECT_URI=(
        "http://127.0.0.1:8000/"
        "api/auth/identity/google/callback/"
    ),
)
class H2B3D3DRegistrationLoginUXTests(
    TestCase,
):

    def setUp(self):
        self.client = APIClient()


    def create_pending(
        self,
        *,
        email=(
            "pending-d3d@oneuch.test"
        ),
        subject=(
            "pending-d3d-subject"
        ),
    ):
        registration, created = (
            submit_registration_request(
                provider=(
                    AUTH_METHOD_GOOGLE
                ),
                issuer=(
                    "https://accounts.google.com"
                ),
                subject=subject,
                email=email,
                organization_name=(
                    "D3D Pending Company"
                ),
                privacy_notice_version=(
                    "privacy-2026-09"
                ),
                terms_version=(
                    "terms-2026-09"
                ),
                consent_recorded_at=(
                    timezone.now()
                ),
                requested_region=(
                    "ap-south-1"
                ),
            )
        )

        self.assertTrue(created)

        return registration


    def sign_in_callback(
        self,
        *,
        claims,
    ):
        start = self.client.get(
            (
                "/api/auth/identity/"
                "google/start/"
            )
        )

        self.assertEqual(
            start.status_code,
            302,
        )

        provider_url = (
            start["Location"]
        )

        state = (
            parse_qs(
                urlsplit(
                    provider_url
                ).query
            )[
                "state"
            ][0]
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
                    "google/callback/"
                ),
                {
                    "code":
                        "synthetic-d3d-code",

                    "state":
                        state,
                },
            )


    def query(self, response):
        return parse_qs(
            urlsplit(
                response[
                    "Location"
                ]
            ).query
        )


    def claims_for(
        self,
        registration,
    ):
        identity = (
            registration
            .user
            .external_identities
            .get(
                provider=(
                    AUTH_METHOD_GOOGLE
                )
            )
        )

        return IdentityClaims(
            provider=(
                AUTH_METHOD_GOOGLE
            ),
            issuer=(
                identity.issuer
            ),
            subject=(
                identity.subject
            ),
            email=(
                registration.user.email
            ),
        )


    def test_exact_pending_identity_signin_reports_pending(
        self,
    ):
        registration = (
            self.create_pending()
        )

        response = (
            self.sign_in_callback(
                claims=(
                    self.claims_for(
                        registration
                    )
                ),
            )
        )

        query = self.query(
            response
        )

        self.assertEqual(
            query[
                "registration_status"
            ][0],
            REGISTRATION_STATUS_PENDING,
        )

        self.assertEqual(
            query[
                "registration_id"
            ][0],
            registration.public_id,
        )

        self.assertEqual(
            query[
                "registration_created"
            ][0],
            "0",
        )

        self.assertNotIn(
            "identity_code",
            query,
        )

        self.assertNotIn(
            "identity_error",
            query,
        )


    def test_exact_rejected_identity_signin_reports_rejected(
        self,
    ):
        registration = (
            self.create_pending(
                email=(
                    "rejected-d3d@oneuch.test"
                ),
                subject=(
                    "rejected-d3d-subject"
                ),
            )
        )

        reviewer = (
            User.objects.create_user(
                email=(
                    "reviewer-d3d@oneuch.test"
                ),
                password=(
                    "OneUCH!ReviewerD3D93471"
                ),
                is_active=True,
                is_staff=True,
            )
        )

        reject_registration_request(
            registration_public_id=(
                registration.public_id
            ),
            reviewer=reviewer,
            rejection_reason=(
                "Registration not approved."
            ),
        )

        response = (
            self.sign_in_callback(
                claims=(
                    self.claims_for(
                        registration
                    )
                ),
            )
        )

        query = self.query(
            response
        )

        self.assertEqual(
            query[
                "registration_status"
            ][0],
            REGISTRATION_STATUS_REJECTED,
        )

        self.assertEqual(
            query[
                "registration_id"
            ][0],
            registration.public_id,
        )

        self.assertNotIn(
            "identity_code",
            query,
        )


    def test_unknown_verified_identity_remains_generic_failure(
        self,
    ):
        claims = IdentityClaims(
            provider=(
                AUTH_METHOD_GOOGLE
            ),
            issuer=(
                "https://accounts.google.com"
            ),
            subject=(
                "unknown-d3d-subject"
            ),
            email=(
                "unknown-d3d@oneuch.test"
            ),
        )

        response = (
            self.sign_in_callback(
                claims=claims
            )
        )

        query = self.query(
            response
        )

        self.assertEqual(
            query[
                "identity_error"
            ][0],
            "signin_failed",
        )

        self.assertNotIn(
            "registration_status",
            query,
        )


    def test_status_lookup_never_uses_email_only_matching(
        self,
    ):
        registration = (
            self.create_pending(
                email=(
                    "no-email-match-d3d@oneuch.test"
                ),
                subject=(
                    "correct-d3d-subject"
                ),
            )
        )

        state = (
            registration_review_state_for_verified_identity(
                provider=(
                    AUTH_METHOD_GOOGLE
                ),
                issuer=(
                    "https://accounts.google.com"
                ),
                subject=(
                    "wrong-d3d-subject"
                ),
            )
        )

        self.assertIsNone(
            state
        )


    def test_status_lookup_returns_only_pending_or_rejected(
        self,
    ):
        registration = (
            self.create_pending(
                email=(
                    "state-d3d@oneuch.test"
                ),
                subject=(
                    "state-d3d-subject"
                ),
            )
        )

        state = (
            registration_review_state_for_verified_identity(
                provider=(
                    AUTH_METHOD_GOOGLE
                ),
                issuer=(
                    "https://accounts.google.com"
                ),
                subject=(
                    "state-d3d-subject"
                ),
            )
        )

        self.assertEqual(
            state[
                "status"
            ],
            REGISTRATION_STATUS_PENDING,
        )

        self.assertEqual(
            state[
                "registration_id"
            ],
            registration.public_id,
        )
