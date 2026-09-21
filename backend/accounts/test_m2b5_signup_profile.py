from urllib.parse import (
    parse_qs,
    urlsplit,
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
    IDENTITY_REGISTRATION_CONTEXT_COOKIE,
    resolve_identity_callback_state,
)

from accounts.models import (
    AUTH_METHOD_GOOGLE,
)

from accounts.registration_service import (
    RegistrationValidationError,
    submit_registration_request,
)

from accounts.registration_views import (
    build_safe_registration_payload,
)


@override_settings(
    AUTH_IDENTITY_SIGNIN_ENABLED=True,
    AUTH_GOVERNED_REGISTRATION_ENABLED=True,
    AUTH_IDENTITY_STATE_MAX_AGE_SECONDS=600,
    ONEUCH_PRIVACY_NOTICE_VERSION="privacy-test",
    ONEUCH_TERMS_VERSION="terms-test",
    ONEUCH_REGION="ap-south-1",
    GOOGLE_IDENTITY_CLIENT_ID="synthetic-google-client",
    GOOGLE_IDENTITY_CLIENT_SECRET="synthetic-google-secret",
    GOOGLE_IDENTITY_REDIRECT_URI=(
        "https://api.oneuch.test/"
        "api/auth/identity/google/callback/"
    ),
)
class M2B5SignupProfileTests(
    TestCase,
):

    def setUp(self):
        self.client = APIClient()


    def registration_payload(
        self,
    ):
        return {
            "first_name":
                "Nirav",

            "last_name":
                "Shah",

            "phone_number":
                "+91 98765 43210",

            "organization_name":
                "Profile Test Company",

            "acknowledged":
                True,
        }


    def test_public_signup_requires_first_and_last_name(
        self,
    ):
        payload = (
            self.registration_payload()
        )

        payload["first_name"] = ""

        response = self.client.post(
            (
                "/api/auth/identity/"
                "registration/google/start/"
            ),
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )


        payload = (
            self.registration_payload()
        )

        payload["last_name"] = ""

        response = self.client.post(
            (
                "/api/auth/identity/"
                "registration/google/start/"
            ),
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )


    def test_service_requires_profile_names(
        self,
    ):
        with self.assertRaises(
            RegistrationValidationError
        ):
            submit_registration_request(
                provider=(
                    AUTH_METHOD_GOOGLE
                ),
                issuer=(
                    "https://accounts.google.com"
                ),
                subject=(
                    "missing-profile-subject"
                ),
                email=(
                    "missing-profile@oneuch.test"
                ),
                organization_name=(
                    "Missing Profile"
                ),
                privacy_notice_version=(
                    "privacy-test"
                ),
                terms_version=(
                    "terms-test"
                ),
                consent_recorded_at=(
                    timezone.now()
                ),
            )


    def test_profile_survives_signed_oauth_context(
        self,
    ):
        response = self.client.post(
            (
                "/api/auth/identity/"
                "registration/google/start/"
            ),
            self.registration_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        state = (
            parse_qs(
                urlsplit(
                    response.data[
                        "authorization_url"
                    ]
                ).query
            )[
                "state"
            ][0]
        )

        context_cookie = (
            response.cookies[
                IDENTITY_REGISTRATION_CONTEXT_COOKIE
            ].value
        )

        transaction = (
            resolve_identity_callback_state(
                provider=(
                    AUTH_METHOD_GOOGLE
                ),
                state=state,
                signin_browser_binding=None,
                registration_context_cookie=(
                    context_cookie
                ),
            )
        )

        profile = (
            transaction[
                "registration"
            ]
        )

        self.assertEqual(
            profile["first_name"],
            "Nirav",
        )

        self.assertEqual(
            profile["last_name"],
            "Shah",
        )

        self.assertEqual(
            profile["phone_number"],
            "+91 98765 43210",
        )


    def test_pending_user_and_review_payload_store_profile(
        self,
    ):
        (
            registration,
            created,
        ) = submit_registration_request(
            provider=(
                AUTH_METHOD_GOOGLE
            ),
            issuer=(
                "https://accounts.google.com"
            ),
            subject=(
                "m2b5-profile-subject"
            ),
            email=(
                "m2b5-profile@oneuch.test"
            ),
            organization_name=(
                "Profile Company"
            ),
            privacy_notice_version=(
                "privacy-test"
            ),
            terms_version=(
                "terms-test"
            ),
            consent_recorded_at=(
                timezone.now()
            ),
            requested_region=(
                "ap-south-1"
            ),
            first_name="Nirav",
            last_name="Shah",
            phone_number=(
                "+91 98765 43210"
            ),
        )

        self.assertTrue(
            created
        )

        user = registration.user

        self.assertEqual(
            user.first_name,
            "Nirav",
        )

        self.assertEqual(
            user.last_name,
            "Shah",
        )

        self.assertEqual(
            user.phone_number,
            "+91 98765 43210",
        )

        self.assertFalse(
            user.has_usable_password()
        )

        self.assertFalse(
            user.is_active
        )

        review_payload = (
            build_safe_registration_payload(
                registration
            )
        )

        self.assertEqual(
            review_payload[
                "user"
            ][
                "first_name"
            ],
            "Nirav",
        )

        self.assertEqual(
            review_payload[
                "user"
            ][
                "last_name"
            ],
            "Shah",
        )

        self.assertEqual(
            review_payload[
                "user"
            ][
                "phone_number"
            ],
            "+91 98765 43210",
        )
