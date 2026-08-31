from pathlib import (
    Path,
)

from django.core.checks import (
    Tags,
    WARNING,
    run_checks,
)

from django.db.migrations.executor import (
    MigrationExecutor,
)

from backend.deployment_validation import (
    collect_pilot_configuration_errors,
)


EXPECTED_ASGI_APPLICATION = (
    "backend.asgi.application"
)

EXPECTED_BEAT_SCHEDULER = (
    "django_celery_beat.schedulers:"
    "DatabaseScheduler"
)


def _collect_django_deployment_errors(
    *,
    run_checks_fn,
):
    errors = []

    messages = run_checks_fn(
        tags=[
            Tags.security,
        ],
        include_deployment_checks=True,
    )

    for message in messages:

        if message.level >= WARNING:

            check_id = (
                message.id
                or "deployment-check"
            )

            errors.append(
                "Django deployment check "
                f"{check_id}: "
                f"{message.msg}"
            )

    return errors


def _collect_runtime_wiring_errors(
    settings_obj,
):
    errors = []


    if (
        settings_obj.ASGI_APPLICATION
        != EXPECTED_ASGI_APPLICATION
    ):
        errors.append(
            "ASGI_APPLICATION must be "
            f"{EXPECTED_ASGI_APPLICATION}."
        )


    if (
        settings_obj.CELERY_BROKER_URL
        != settings_obj.REDIS_URL
    ):
        errors.append(
            "CELERY_BROKER_URL must use REDIS_URL."
        )


    if (
        settings_obj.CELERY_RESULT_BACKEND
        != settings_obj.REDIS_URL
    ):
        errors.append(
            "CELERY_RESULT_BACKEND must use REDIS_URL."
        )


    channel_hosts = (
        settings_obj
        .CHANNEL_LAYERS
        .get(
            "default",
            {},
        )
        .get(
            "CONFIG",
            {},
        )
        .get(
            "hosts",
            [],
        )
    )


    if (
        settings_obj.REDIS_URL
        not in channel_hosts
    ):
        errors.append(
            "Django Channels must use REDIS_URL."
        )


    if (
        settings_obj.CELERY_BEAT_SCHEDULER
        != EXPECTED_BEAT_SCHEDULER
    ):
        errors.append(
            "CELERY_BEAT_SCHEDULER must use "
            "django-celery-beat DatabaseScheduler."
        )


    return errors


def _collect_database_errors(
    *,
    connection_obj,
    migration_executor_cls,
):
    errors = []


    if (
        connection_obj.vendor
        != "postgresql"
    ):
        errors.append(
            "Runtime database vendor must be PostgreSQL."
        )

        return errors


    try:

        with connection_obj.cursor() as cursor:

            cursor.execute(
                "SELECT 1"
            )

            row = cursor.fetchone()

            if (
                not row
                or row[0] != 1
            ):
                errors.append(
                    "PostgreSQL connectivity probe "
                    "returned an unexpected result."
                )

    except Exception:

        errors.append(
            "PostgreSQL connectivity probe failed."
        )

        return errors


    try:

        executor = (
            migration_executor_cls(
                connection_obj
            )
        )

        leaf_nodes = (
            executor
            .loader
            .graph
            .leaf_nodes()
        )

        migration_plan = (
            executor.migration_plan(
                leaf_nodes
            )
        )

        if migration_plan:

            errors.append(
                "Unapplied Django migrations remain."
            )

    except Exception:

        errors.append(
            "Unable to determine Django migration readiness."
        )


    return errors


def _collect_redis_errors(
    *,
    redis_client,
):
    try:

        result = redis_client.ping()

        if result is not True:
            return [
                "Redis connectivity probe "
                "did not return PONG."
            ]

    except Exception:

        return [
            "Redis connectivity probe failed."
        ]


    return []


def _collect_static_errors(
    *,
    static_root,
):
    root = Path(
        static_root
    )


    if (
        not root.exists()
        or not root.is_dir()
    ):
        return [
            "STATIC_ROOT does not exist. "
            "Run collectstatic before the pilot release gate."
        ]


    has_static_file = any(
        path.is_file()
        for path
        in root.rglob("*")
    )


    if not has_static_file:
        return [
            "STATIC_ROOT contains no collected static files."
        ]


    return []


def collect_pilot_release_errors(
    *,
    settings_obj,
    connection_obj,
    redis_client,
    run_checks_fn=run_checks,
    migration_executor_cls=MigrationExecutor,
):
    """
    Final One UCH pilot release gate.

    This is intended to run on the actual pilot application
    host after environment configuration, migrations and
    collectstatic have been prepared.

    No secrets or credential values are returned in errors.
    """

    errors = []


    errors.extend(
        collect_pilot_configuration_errors(
            settings_obj
        )
    )


    errors.extend(
        _collect_django_deployment_errors(
            run_checks_fn=run_checks_fn
        )
    )


    errors.extend(
        _collect_runtime_wiring_errors(
            settings_obj
        )
    )


    errors.extend(
        _collect_database_errors(
            connection_obj=connection_obj,
            migration_executor_cls=(
                migration_executor_cls
            ),
        )
    )


    errors.extend(
        _collect_redis_errors(
            redis_client=redis_client
        )
    )


    errors.extend(
        _collect_static_errors(
            static_root=(
                settings_obj.STATIC_ROOT
            )
        )
    )


    return errors
