from types import (
    SimpleNamespace,
)

from django.test import (
    SimpleTestCase,
)

from backend.deployment_validation import (
    collect_pilot_configuration_errors,
)


def secure_pilot_settings(
    **overrides,
):
    values = {
        "DEBUG":
            False,

        "SECRET_KEY":
            (
                "pilot-secret-key-"
                "012345678901234567890123456789"
            ),

        "ALLOWED_HOSTS": [
            "api.oneuch.example",
        ],

        "DATABASES": {
            "default": {
                "ENGINE":
                    "django.db.backends.postgresql",
            },
        },

        "CORS_ALLOW_ALL_ORIGINS":
            False,

        "CORS_ALLOWED_ORIGINS": [
            "https://app.oneuch.example",
        ],

        "SECURE_SSL_REDIRECT":
            True,

        "SESSION_COOKIE_SECURE":
            True,

        "CSRF_COOKIE_SECURE":
            True,

        "SECURE_HSTS_SECONDS":
            3600,

        "SECURE_PROXY_SSL_HEADER": (
            "HTTP_X_FORWARDED_PROTO",
            "https",
        ),

        "GOOGLE_REDIRECT_URI": (
            "https://api.oneuch.example/"
            "api/google/oauth/callback/"
        ),

        "MICROSOFT_REDIRECT_URI": (
            "https://api.oneuch.example/"
            "api/microsoft/oauth/callback/"
        ),
    }

    values.update(
        overrides
    )

    return SimpleNamespace(
        **values
    )


class PilotDeploymentValidationTests(
    SimpleTestCase
):

    def test_secure_pilot_configuration_passes(
        self,
    ):
        errors = (
            collect_pilot_configuration_errors(
                secure_pilot_settings()
            )
        )

        self.assertEqual(
            errors,
            [],
        )


    def test_development_configuration_is_rejected(
        self,
    ):
        errors = (
            collect_pilot_configuration_errors(
                secure_pilot_settings(
                    DEBUG=True,
                    DATABASES={
                        "default": {
                            "ENGINE":
                                "django.db.backends.sqlite3",
                        },
                    },
                    CORS_ALLOW_ALL_ORIGINS=True,
                    SECURE_SSL_REDIRECT=False,
                    SESSION_COOKIE_SECURE=False,
                    CSRF_COOKIE_SECURE=False,
                    SECURE_HSTS_SECONDS=0,
                )
            )
        )

        joined = "\n".join(
            errors
        )

        self.assertIn(
            "DEBUG must be False",
            joined,
        )

        self.assertIn(
            "PostgreSQL",
            joined,
        )

        self.assertIn(
            "CORS_ALLOW_ALL_ORIGINS",
            joined,
        )

        self.assertIn(
            "SECURE_SSL_REDIRECT",
            joined,
        )


    def test_wildcard_and_local_hosts_are_rejected(
        self,
    ):
        errors = (
            collect_pilot_configuration_errors(
                secure_pilot_settings(
                    ALLOWED_HOSTS=[
                        "*",
                        "localhost",
                    ],
                )
            )
        )

        joined = "\n".join(
            errors
        )

        self.assertIn(
            "pilot-unsafe host '*'",
            joined,
        )

        self.assertIn(
            "pilot-unsafe host 'localhost'",
            joined,
        )


    def test_insecure_public_origins_and_callbacks_are_rejected(
        self,
    ):
        errors = (
            collect_pilot_configuration_errors(
                secure_pilot_settings(
                    CORS_ALLOWED_ORIGINS=[
                        "http://localhost:5173",
                    ],
                    GOOGLE_REDIRECT_URI=(
                        "http://127.0.0.1:8000/"
                        "api/google/oauth/callback/"
                    ),
                    MICROSOFT_REDIRECT_URI=(
                        "http://localhost:8000/"
                        "api/microsoft/oauth/callback/"
                    ),
                )
            )
        )

        joined = "\n".join(
            errors
        )

        self.assertIn(
            "CORS_ALLOWED_ORIGINS entry must use HTTPS",
            joined,
        )

        self.assertIn(
            "GOOGLE_REDIRECT_URI must use HTTPS",
            joined,
        )

        self.assertIn(
            "MICROSOFT_REDIRECT_URI must use HTTPS",
            joined,
        )
