from pathlib import (
    Path,
)

from tempfile import (
    TemporaryDirectory,
)

from types import (
    SimpleNamespace,
)

from django.core.checks import (
    Tags,
    WARNING,
)

from django.test import (
    SimpleTestCase,
)

from backend.pilot_release_gate import (
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

    def __init__(
        self,
        *,
        result=True,
        error=None,
    ):
        self.result = result
        self.error = error


    def ping(
        self,
    ):
        if self.error:
            raise self.error

        return self.result


class FakeGraph:

    def leaf_nodes(
        self,
    ):
        return [
            (
                "accounts",
                "0001_initial",
            ),
        ]


class FakeLoader:

    graph = FakeGraph()


class CleanMigrationExecutor:

    def __init__(
        self,
        connection,
    ):
        self.connection = connection
        self.loader = FakeLoader()


    def migration_plan(
        self,
        leaf_nodes,
    ):
        return []


class PendingMigrationExecutor(
    CleanMigrationExecutor
):

    def migration_plan(
        self,
        leaf_nodes,
    ):
        return [
            (
                "pending-migration",
                False,
            ),
        ]


def secure_settings(
    static_root,
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


class PilotReleaseGateTests(
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
            "pilot-static-ready",
            encoding="utf-8",
        )

        return static_root


    def test_secure_runtime_passes_release_gate(
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
                        secure_settings(
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
                        CleanMigrationExecutor
                    ),
                )
            )


        self.assertEqual(
            errors,
            [],
        )


    def test_django_deployment_warning_blocks_release(
        self,
    ):

        with TemporaryDirectory() as temp:

            static_root = (
                self.build_static_root(
                    temp
                )
            )

            warning = SimpleNamespace(
                level=WARNING,
                id="security.W999",
                msg="Synthetic deployment warning.",
            )

            errors = (
                collect_pilot_release_errors(
                    settings_obj=(
                        secure_settings(
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
                        lambda **kwargs: [
                            warning,
                        ]
                    ),
                    migration_executor_cls=(
                        CleanMigrationExecutor
                    ),
                )
            )


        self.assertTrue(
            any(
                "security.W999"
                in error
                for error
                in errors
            )
        )


    def test_release_gate_requests_security_deployment_checks_only(
        self,
    ):

        with TemporaryDirectory() as temp:

            static_root = (
                self.build_static_root(
                    temp
                )
            )

            calls = []


            def security_checks_probe(
                **kwargs,
            ):

                calls.append(
                    kwargs
                )

                return []


            errors = (
                collect_pilot_release_errors(
                    settings_obj=(
                        secure_settings(
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
                        security_checks_probe
                    ),
                    migration_executor_cls=(
                        CleanMigrationExecutor
                    ),
                )
            )


        self.assertEqual(
            errors,
            [],
        )

        self.assertEqual(
            len(calls),
            1,
        )

        self.assertEqual(
            calls[0].get(
                "tags"
            ),
            [
                Tags.security,
            ],
        )

        self.assertTrue(
            calls[0].get(
                "include_deployment_checks"
            )
        )


    def test_pending_migration_blocks_release(
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
                        secure_settings(
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
                        PendingMigrationExecutor
                    ),
                )
            )


        self.assertIn(
            "Unapplied Django migrations remain.",
            errors,
        )


    def test_redis_and_static_failure_block_release(
        self,
    ):

        with TemporaryDirectory() as temp:

            missing_static = (
                Path(temp)
                / "missing-static"
            )

            errors = (
                collect_pilot_release_errors(
                    settings_obj=(
                        secure_settings(
                            missing_static
                        )
                    ),
                    connection_obj=(
                        FakeConnection()
                    ),
                    redis_client=(
                        FakeRedis(
                            error=RuntimeError(
                                "redis unavailable"
                            )
                        )
                    ),
                    run_checks_fn=(
                        lambda **kwargs: []
                    ),
                    migration_executor_cls=(
                        CleanMigrationExecutor
                    ),
                )
            )


        joined = "\n".join(
            errors
        )

        self.assertIn(
            "Redis connectivity probe failed",
            joined,
        )

        self.assertIn(
            "STATIC_ROOT does not exist",
            joined,
        )


    def test_runtime_wiring_drift_blocks_release(
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
                        secure_settings(
                            static_root,
                            ASGI_APPLICATION=(
                                "wrong.application"
                            ),
                            CELERY_BROKER_URL=(
                                "redis://wrong:6379/0"
                            ),
                            CHANNEL_LAYERS={
                                "default": {
                                    "CONFIG": {
                                        "hosts": [
                                            "redis://wrong:6379/0",
                                        ],
                                    },
                                },
                            },
                            CELERY_BEAT_SCHEDULER=(
                                "wrong.scheduler"
                            ),
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
                        CleanMigrationExecutor
                    ),
                )
            )


        joined = "\n".join(
            errors
        )

        self.assertIn(
            "ASGI_APPLICATION",
            joined,
        )

        self.assertIn(
            "CELERY_BROKER_URL",
            joined,
        )

        self.assertIn(
            "Django Channels",
            joined,
        )

        self.assertIn(
            "CELERY_BEAT_SCHEDULER",
            joined,
        )
