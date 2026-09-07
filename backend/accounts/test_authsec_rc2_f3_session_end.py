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
)
from accounts.models import (
    AUTH_METHOD_WORK_EMAIL,
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
class AuthSecRC2F3SessionEndTests(
    TestCase,
):

    PASSWORD = (
        "OneUCH!F3Session93471"
    )

    def setUp(
        self,
    ):
        cache.clear()

        self.client = APIClient()

        self.user = (
            User.objects.create_user(
                email=(
                    "browser-f3@oneuch.test"
                ),
                password=self.PASSWORD,
                signup_method=(
                    AUTH_METHOD_WORK_EMAIL
                ),
            )
        )

        organization = (
            Organization.objects.create(
                name=(
                    "F3 Browser Workspace"
                ),
                slug=(
                    "f3-browser-workspace"
                ),
                is_active=True,
            )
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=organization,
            role="owner",
        )


    def establish_session(
        self,
    ):
        csrf_response = (
            self.client.get(
                "/api/auth/session/csrf/"
            )
        )

        self.assertEqual(
            csrf_response.status_code,
            200,
        )

        csrf_token = (
            csrf_response.data[
                "csrf_token"
            ]
        )

        login_response = (
            self.client.post(
                "/api/auth/session/login/",
                {
                    "email":
                        self.user.email,

                    "password":
                        self.PASSWORD,
                },
                format="json",
                HTTP_X_ONEUCH_CSRF=(
                    csrf_token
                ),
            )
        )

        self.assertEqual(
            login_response.status_code,
            200,
        )

        self.assertIn(
            BROWSER_REFRESH_COOKIE,
            login_response.cookies,
        )

        return csrf_token


    def test_session_end_requires_csrf(
        self,
    ):
        self.establish_session()

        response = self.client.post(
            "/api/auth/session/end/",
            {},
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


    def test_session_end_clears_refresh_and_csrf_cookies_without_token_payload(
        self,
    ):
        csrf_token = (
            self.establish_session()
        )

        response = self.client.post(
            "/api/auth/session/end/",
            {},
            format="json",
            HTTP_X_ONEUCH_CSRF=(
                csrf_token
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            response.data[
                "ended"
            ]
        )

        self.assertNotIn(
            "access",
            response.data,
        )

        self.assertNotIn(
            "refresh",
            response.data,
        )

        for cookie_name in (
            BROWSER_REFRESH_COOKIE,
            BROWSER_CSRF_COOKIE,
        ):
            self.assertIn(
                cookie_name,
                response.cookies,
            )

            self.assertEqual(
                response.cookies[
                    cookie_name
                ][
                    "max-age"
                ],
                0,
            )
