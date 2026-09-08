from pathlib import (
    Path,
)
from tempfile import (
    TemporaryDirectory,
)
from types import (
    SimpleNamespace,
)

from django.test import (
    SimpleTestCase,
)

from backend.deployment_validation import (
    collect_pilot_configuration_errors,
)
from backend.pilot_release_gate import (
    BROWSER_SESSION_MIGRATION_ERROR,
    collect_pilot_release_errors,
)


class FakeCursor:

    def __enter__(
        self,
    ):
        return self


    def __exit__(
        self,
        exc_type,
        exc,
        traceback,
    ):
        return False


    def execute(
        self,
        sql,
    ):
        if sql != "SELECT 1":
            raise AssertionError(
                f"Unexpected SQL: {sql}"
            )


    def fetchone(
        self,
    ):
        return (
            1,
        )


class FakeConnection:

    vendor = "postgresql"


    def cursor(
        self,
    ):
        return FakeCursor()


class FakeRedis:

    def ping(
        self,
    ):
        return True


class FakeGraph:

    def leaf_nodes(
        self,
    ):
        return [
            (
                "accounts",
                "0005_authsec_rc2_browser_session",
            ),
        ]


class AppliedBrowserSessionLoader:

    graph = FakeGraph()

    applied_migrations = {
        (
            "accounts",
            "0005_authsec_rc2_browser_session",
        ):
            object(),
    }


class MissingBrowserSessionLoader:

    graph = FakeGraph()

    applied_migrations = {}


class AppliedBrowserSessionExecutor:

    def __init__(
        self,
        connection,
    ):
        self.connection = connection
        self.loader = (
            AppliedBrowserSessionLoader()
        )


    def migration_plan(
        self,
        leaf_nodes,
    ):
        return []


class MissingBrowserSessionExecutor:

    def __init__(
        self,
        connection,
    ):
        self.connection = connection
        self.loader = (
            MissingBrowserSessionLoader()
        )


    def migration_plan(
        self,
        leaf_nodes,
    ):
        # Deliberately clean so this test proves the explicit
        # browser-session migration requirement rather than
        # merely the generic pending-migration gate.
        return []


def secure_f5_settings(
    static_root=None,
    **overrides,
):
    values = {
        "DEBUG":
            False,

        "SECRET_KEY": (
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

        "CORS_ALLOW_CREDENTIALS":
            True,

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

        "AUTH_IDENTITY_SIGNIN_ENABLED":
            False,

        "AUTH_BROWSER_SESSION_ENABLED":
            True,

        "REDIS_URL":
            "redis://127.0.0.1:6379/0",

        "CELERY_BROKER_URL":
            "redis://127.0.0.1:6379/0",

        "CELERY_RESULT_BACKEND":
            "redis://127.0.0.1:6379/0",

        "CHANNEL_LAYERS": {
            "default": {
                "CONFIG": {
                    "hosts": [
                        "redis://127.0.0.1:6379/0",
                    ],
                },
            },
        },

        "CELERY_BEAT_SCHEDULER": (
            "django_celery_beat.schedulers:"
            "DatabaseScheduler"
        ),

        "ASGI_APPLICATION":
            "backend.asgi.application",

        "STATIC_ROOT":
            static_root,
    }


    values.update(
        overrides
    )


    return SimpleNamespace(
        **values
    )


class AuthSecRC2F5PilotSessionReleaseTests(
    SimpleTestCase
):

    def build_static_root(
        self,
        root,
    ):
        static_root = (
            Path(root)
            / "staticfiles"
        )

        static_root.mkdir(
            parents=True
        )

        (
            static_root
            / "manifest.txt"
        ).write_text(
            "authsec-rc2-f5",
            encoding="utf-8",
        )

        return static_root


    def test_enabled_browser_session_secure_configuration_passes(
        self,
    ):
        errors = (
            collect_pilot_configuration_errors(
                secure_f5_settings()
            )
        )

        self.assertEqual(
            errors,
            [],
        )


    def test_enabled_browser_session_requires_cors_credentials(
        self,
    ):
        errors = (
            collect_pilot_configuration_errors(
                secure_f5_settings(
                    CORS_ALLOW_CREDENTIALS=False,
                )
            )
        )

        self.assertIn(
            (
                "CORS_ALLOW_CREDENTIALS must be True when "
                "browser session authentication is enabled."
            ),
            errors,
        )


    def test_enabled_browser_session_release_passes_after_0005_is_applied(
        self,
    ):
        with TemporaryDirectory() as temp:

            static_root = (
                self.build_static_root(
                    temp
                )
            )

            errors = (
                collect_pilot_release_errors(
                    settings_obj=(
                        secure_f5_settings(
                            static_root
                        )
                    ),
                    connection_obj=(
                        FakeConnection()
                    ),
                    redis_client=(
                        FakeRedis()
                    ),
                    run_checks_fn=(
                        lambda **kwargs: []
                    ),
                    migration_executor_cls=(
                        AppliedBrowserSessionExecutor
                    ),
                )
            )


        self.assertEqual(
            errors,
            [],
        )


    def test_enabled_browser_session_release_rejects_missing_0005_even_with_clean_plan(
        self,
    ):
        with TemporaryDirectory() as temp:

            static_root = (
                self.build_static_root(
                    temp
                )
            )

            errors = (
                collect_pilot_release_errors(
                    settings_obj=(
                        secure_f5_settings(
                            static_root
                        )
                    ),
                    connection_obj=(
                        FakeConnection()
                    ),
                    redis_client=(
                        FakeRedis()
                    ),
                    run_checks_fn=(
                        lambda **kwargs: []
                    ),
                    migration_executor_cls=(
                        MissingBrowserSessionExecutor
                    ),
                )
            )


        self.assertIn(
            BROWSER_SESSION_MIGRATION_ERROR,
            errors,
        )


    def test_disabled_browser_session_does_not_require_explicit_0005_activation_check(
        self,
    ):
        with TemporaryDirectory() as temp:

            static_root = (
                self.build_static_root(
                    temp
                )
            )

            errors = (
                collect_pilot_release_errors(
                    settings_obj=(
                        secure_f5_settings(
                            static_root,
                            AUTH_BROWSER_SESSION_ENABLED=False,
                        )
                    ),
                    connection_obj=(
                        FakeConnection()
                    ),
                    redis_client=(
                        FakeRedis()
                    ),
                    run_checks_fn=(
                        lambda **kwargs: []
                    ),
                    migration_executor_cls=(
                        MissingBrowserSessionExecutor
                    ),
                )
            )


        self.assertNotIn(
            BROWSER_SESSION_MIGRATION_ERROR,
            errors,
        )
