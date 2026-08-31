
from unittest.mock import (
    patch,
)

from django.contrib.auth import (
    get_user_model,
)

from django.test import (
    TestCase,
)

from rest_framework.test import (
    APIClient,
)

from inbox.models import (
    Organization,
    OrganizationUser,
)


User = get_user_model()


class PilotUserSmokeTests(
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
                    "pilot-smoke@oneuch.test"
                ),
                password=self.password,
            )
        )

        organization = (
            Organization.objects.create(
                name="Pilot Smoke Org",
                slug="pilot-smoke-org",
            )
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=organization,
            role="member",
        )

        self.client = APIClient()


    @patch(
        "platform_core.monitoring.monitor."
        "settings.REDIS_CLIENT"
    )
    def test_login_to_protected_pilot_surfaces(
        self,
        redis_client,
    ):

        redis_client.ping.return_value = True


        login = self.client.post(
            "/api/auth/token/",
            {
                "email": self.user.email,
                "password": self.password,
            },
            format="json",
        )

        self.assertEqual(
            login.status_code,
            200,
        )

        self.assertIn(
            "access",
            login.data,
        )

        self.assertIn(
            "refresh",
            login.data,
        )


        access = login.data[
            "access"
        ]

        self.client.credentials(
            HTTP_AUTHORIZATION=(
                f"Bearer {access}"
            )
        )


        health = self.client.get(
            "/api/platform/health/"
        )

        self.assertEqual(
            health.status_code,
            200,
        )


        adoption = self.client.get(
            "/api/mail-adoption/"
        )

        self.assertEqual(
            adoption.status_code,
            200,
        )

        self.assertEqual(
            adoption.data[
                "summary"
            ][
                "supported"
            ],
            2,
        )


        google = self.client.get(
            "/api/google/oauth/start/"
        )

        self.assertEqual(
            google.status_code,
            200,
        )

        google_payload = (
            google.json()
        )

        self.assertIn(
            "accounts.google.com",
            google_payload[
                "authorization_url"
            ],
        )

        self.assertIn(
            "state=",
            google_payload[
                "authorization_url"
            ],
        )


        microsoft = self.client.get(
            "/api/microsoft/oauth/start/"
        )

        self.assertEqual(
            microsoft.status_code,
            200,
        )

        self.assertIn(
            "login.microsoftonline.com",
            microsoft.data[
                "authorization_url"
            ],
        )

        self.assertIn(
            "state=",
            microsoft.data[
                "authorization_url"
            ],
        )
