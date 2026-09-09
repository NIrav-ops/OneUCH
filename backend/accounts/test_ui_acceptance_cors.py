from corsheaders.defaults import (
    default_headers,
)

from django.conf import settings
from django.test import (
    SimpleTestCase,
    override_settings,
)


FRONTEND_ORIGIN = (
    "http://localhost:5173"
)


class UIAcceptanceBrowserSessionCorsTests(
    SimpleTestCase
):

    def test_oneuch_csrf_header_extends_cors_defaults(
        self,
    ):
        allowed = {
            str(header).lower()
            for header
            in settings.CORS_ALLOW_HEADERS
        }

        self.assertIn(
            "x-oneuch-csrf",
            allowed,
        )

        for required_default in (
            "authorization",
            "content-type",
        ):
            self.assertIn(
                required_default,
                allowed,
            )

        self.assertTrue(
            set(
                default_headers
            ).issubset(
                allowed
            )
        )


    @override_settings(
        CORS_ALLOW_ALL_ORIGINS=True,
        CORS_ALLOW_CREDENTIALS=True,
        AUTH_BROWSER_SESSION_ENABLED=True,
        DEBUG=True,
    )
    def test_browser_login_preflight_allows_oneuch_csrf(
        self,
    ):
        response = self.client.options(
            "/api/auth/session/login/",
            HTTP_ORIGIN=(
                FRONTEND_ORIGIN
            ),
            HTTP_ACCESS_CONTROL_REQUEST_METHOD=(
                "POST"
            ),
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS=(
                "content-type,x-oneuch-csrf"
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        allow_headers = str(
            response.headers.get(
                "Access-Control-Allow-Headers",
                "",
            )
        ).lower()

        self.assertIn(
            "x-oneuch-csrf",
            allow_headers,
        )

        self.assertEqual(
            response.headers.get(
                "Access-Control-Allow-Origin"
            ),
            FRONTEND_ORIGIN,
        )

        self.assertEqual(
            response.headers.get(
                "Access-Control-Allow-Credentials"
            ),
            "true",
        )


    @override_settings(
        CORS_ALLOW_ALL_ORIGINS=True,
        CORS_ALLOW_CREDENTIALS=True,
        AUTH_BROWSER_SESSION_ENABLED=True,
        DEBUG=True,
    )
    def test_browser_refresh_preflight_allows_oneuch_csrf(
        self,
    ):
        response = self.client.options(
            "/api/auth/session/refresh/",
            HTTP_ORIGIN=(
                FRONTEND_ORIGIN
            ),
            HTTP_ACCESS_CONTROL_REQUEST_METHOD=(
                "POST"
            ),
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS=(
                "content-type,x-oneuch-csrf"
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        allow_headers = str(
            response.headers.get(
                "Access-Control-Allow-Headers",
                "",
            )
        ).lower()

        self.assertIn(
            "x-oneuch-csrf",
            allow_headers,
        )
