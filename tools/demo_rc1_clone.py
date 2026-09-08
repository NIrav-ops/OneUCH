from pathlib import Path
import argparse
import hashlib
import os
import sqlite3
import subprocess
import sys


ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

BACKEND = (
    ROOT
    / "backend"
)

PROTECTED_DB = (
    BACKEND
    / "db.sqlite3"
)

DEMO_ROOT = (
    ROOT
    / "artifacts"
    / "demo_rc1"
)

DEFAULT_TARGET = (
    DEMO_ROOT
    / "demo.sqlite3"
)


REQUIRED_ACCOUNTS_MIGRATIONS = {
    "0003_authsec_rc1a_identity_metadata",
    "0004_auth_rc1b_identity_signin",
    "0005_authsec_rc2_browser_session",
}


CORE_TABLES = {
    "users":
        "accounts_user",

    "organizations":
        "inbox_organization",

    "memberships":
        "inbox_organizationuser",

    "email_accounts":
        "email_accounts_emailaccount",

    "messages":
        "inbox_inboxmessage",

    "conversations":
        "inbox_conversation",

    "sync_status":
        "inbox_inboxsyncstatus",

    "oauth_tokens":
        "oauth_tokens_oauthtoken",
}


class DemoCloneError(
    RuntimeError
):
    pass


def fail(message):
    raise DemoCloneError(
        message
    )


def sha256_file(path):
    digest = hashlib.sha256()

    with Path(path).open(
        "rb"
    ) as handle:

        for block in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(
                block
            )

    return (
        digest.hexdigest()
        .upper()
    )


def is_within(
    path,
    parent,
):
    try:

        Path(path).resolve().relative_to(
            Path(parent).resolve()
        )

        return True

    except ValueError:

        return False


def resolve_demo_target(
    value=None,
):
    target = Path(
        value
        or
        DEFAULT_TARGET
    )


    if not target.is_absolute():
        target = (
            ROOT
            / target
        )


    target = (
        target
        .expanduser()
        .resolve()
    )


    if (
        target
        ==
        PROTECTED_DB.resolve()
    ):
        fail(
            "demo target must never equal protected backend/db.sqlite3"
        )


    if not is_within(
        target,
        DEMO_ROOT,
    ):
        fail(
            "demo target must remain inside artifacts/demo_rc1"
        )


    if (
        target.suffix.lower()
        != ".sqlite3"
    ):
        fail(
            "demo target must use a .sqlite3 file"
        )


    return target


def readonly_connection(path):
    uri = (
        Path(path)
        .resolve()
        .as_uri()
        + "?mode=ro"
    )

    return sqlite3.connect(
        uri,
        uri=True,
    )


def integrity_check(path):
    connection = (
        readonly_connection(
            path
        )
    )

    try:

        row = (
            connection.execute(
                "PRAGMA integrity_check"
            )
            .fetchone()
        )

    finally:

        connection.close()


    if (
        not row
        or
        str(
            row[0]
        ).lower()
        != "ok"
    ):
        fail(
            "SQLite integrity check failed"
        )


def table_exists(
    connection,
    table,
):
    return (
        connection.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type='table'
              AND name=?
            LIMIT 1
            """,
            (
                table,
            ),
        ).fetchone()
        is not None
    )


def collect_inventory(path):
    connection = (
        readonly_connection(
            path
        )
    )

    inventory = {}


    try:

        for label, table in (
            CORE_TABLES.items()
        ):

            if not table_exists(
                connection,
                table,
            ):
                fail(
                    "required demo table missing: "
                    + table
                )


            inventory[label] = int(
                connection.execute(
                    f'SELECT COUNT(*) FROM "{table}"'
                ).fetchone()[0]
            )


    finally:

        connection.close()


    return inventory


def validate_inventory(
    inventory,
):
    required_positive = (
        "users",
        "organizations",
        "memberships",
        "email_accounts",
        "messages",
        "conversations",
    )


    for label in required_positive:

        if int(
            inventory.get(
                label,
                0,
            )
        ) <= 0:
            fail(
                "demo source data missing: "
                + label
            )


def backup_sqlite(
    source,
    target,
    *,
    replace=False,
):
    source = Path(
        source
    ).resolve()

    target = resolve_demo_target(
        target
    )


    if (
        source
        !=
        PROTECTED_DB.resolve()
    ):
        fail(
            "DEMO-RC1 source must be protected backend/db.sqlite3"
        )


    if not source.exists():
        fail(
            "protected source database is missing"
        )


    if target.exists():

        if not replace:
            fail(
                "demo clone already exists; use --replace explicitly"
            )

        target.unlink()


    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


    source_connection = (
        readonly_connection(
            source
        )
    )

    target_connection = sqlite3.connect(
        str(
            target
        )
    )


    try:

        source_connection.backup(
            target_connection
        )

        target_connection.commit()

    finally:

        target_connection.close()
        source_connection.close()


    integrity_check(
        target
    )


    return target


def build_clone_environment(
    target,
    *,
    browser_session_enabled,
    base_environment=None,
):
    target = resolve_demo_target(
        target
    )


    environment = dict(
        base_environment
        if base_environment is not None
        else os.environ
    )


    environment[
        "DJANGO_DB_ENGINE"
    ] = "sqlite"

    environment[
        "ONEUCH_SQLITE_PATH"
    ] = str(
        target
    )

    environment[
        "AUTH_BROWSER_SESSION_ENABLED"
    ] = (
        "true"
        if browser_session_enabled
        else "false"
    )

    environment[
        "CORS_ALLOW_CREDENTIALS"
    ] = "true"


    return environment


def run_manage(
    arguments,
    *,
    environment,
):
    result = subprocess.run(
        [
            sys.executable,
            "manage.py",
            *arguments,
        ],
        cwd=str(
            BACKEND
        ),
        env=environment,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )


    if result.stdout:
        print(
            result.stdout,
            end="",
        )


    if result.stderr:
        print(
            result.stderr,
            end="",
            file=sys.stderr,
        )


    if result.returncode != 0:
        fail(
            "Django child command failed: "
            + " ".join(
                arguments
            )
        )


def applied_accounts_migrations(path):
    connection = (
        readonly_connection(
            path
        )
    )

    try:

        return {
            row[0]

            for row
            in connection.execute(
                """
                SELECT name
                FROM django_migrations
                WHERE app='accounts'
                """
            ).fetchall()
        }

    finally:

        connection.close()


def verify_clone_contract(
    target,
    *,
    expected_inventory=None,
):
    target = resolve_demo_target(
        target
    )


    integrity_check(
        target
    )


    migrations = (
        applied_accounts_migrations(
            target
        )
    )


    missing = (
        REQUIRED_ACCOUNTS_MIGRATIONS
        -
        migrations
    )


    if missing:
        fail(
            "demo clone missing accounts migrations: "
            + ", ".join(
                sorted(
                    missing
                )
            )
        )


    connection = (
        readonly_connection(
            target
        )
    )

    try:

        if not table_exists(
            connection,
            "accounts_browsersession",
        ):
            fail(
                "demo clone BrowserSession table missing"
            )

    finally:

        connection.close()


    inventory = (
        collect_inventory(
            target
        )
    )


    validate_inventory(
        inventory
    )


    if (
        expected_inventory
        is not None
    ):

        for label, expected in (
            expected_inventory.items()
        ):

            actual = inventory.get(
                label
            )

            if actual != expected:
                fail(
                    "demo clone data count mismatch for "
                    + label
                    + ": expected "
                    + str(
                        expected
                    )
                    + ", found "
                    + str(
                        actual
                    )
                )


    return inventory


def prepare_demo_clone(
    *,
    target=None,
    replace=False,
):
    protected = (
        PROTECTED_DB
        .resolve()
    )

    target = resolve_demo_target(
        target
    )


    if not protected.exists():
        fail(
            "protected backend/db.sqlite3 is missing"
        )


    source_hash_before = (
        sha256_file(
            protected
        )
    )


    source_inventory = (
        collect_inventory(
            protected
        )
    )


    validate_inventory(
        source_inventory
    )


    print(
        "PROTECTED_DB="
        + str(
            protected
        )
    )

    print(
        "PROTECTED_DB_SHA256_BEFORE="
        + source_hash_before
    )

    print(
        "DEMO_DB="
        + str(
            target
        )
    )


    backup_sqlite(
        protected,
        target,
        replace=replace,
    )


    print(
        "PASS - protected SQLite copied via backup API"
    )

    print(
        "PASS - clone integrity GREEN"
    )


    # --------------------------------------------------------
    # Migration stage
    #
    # Preserve the Phase-F invariant:
    # migrate required schema BEFORE enabling browser session.
    # --------------------------------------------------------

    migration_environment = (
        build_clone_environment(
            target,
            browser_session_enabled=False,
        )
    )


    print(
        "MIGRATION_ONEUCH_SQLITE_PATH="
        + migration_environment[
            "ONEUCH_SQLITE_PATH"
        ]
    )

    print(
        "MIGRATION_BROWSER_SESSION_ENABLED="
        + migration_environment[
            "AUTH_BROWSER_SESSION_ENABLED"
        ]
    )


    run_manage(
        [
            "migrate",
            "--noinput",
        ],
        environment=(
            migration_environment
        ),
    )


    # --------------------------------------------------------
    # Runtime validation stage
    #
    # Only after migrations are present may browser-session
    # configuration become enabled against the clone.
    # --------------------------------------------------------

    runtime_environment = (
        build_clone_environment(
            target,
            browser_session_enabled=True,
        )
    )


    print(
        "RUNTIME_ONEUCH_SQLITE_PATH="
        + runtime_environment[
            "ONEUCH_SQLITE_PATH"
        ]
    )

    print(
        "RUNTIME_BROWSER_SESSION_ENABLED="
        + runtime_environment[
            "AUTH_BROWSER_SESSION_ENABLED"
        ]
    )


    run_manage(
        [
            "check",
        ],
        environment=(
            runtime_environment
        ),
    )


    clone_inventory = (
        verify_clone_contract(
            target,
            expected_inventory=(
                source_inventory
            ),
        )
    )


    source_hash_after = (
        sha256_file(
            protected
        )
    )


    if (
        source_hash_after
        !=
        source_hash_before
    ):
        fail(
            "protected SQLite changed during clone preparation"
        )


    for label, count in (
        clone_inventory.items()
    ):
        print(
            "CLONE_"
            + label.upper()
            + "="
            + str(
                count
            )
        )


    print(
        "DEMO_CLONE_ACCOUNTS_0003=APPLIED"
    )

    print(
        "DEMO_CLONE_ACCOUNTS_0004=APPLIED"
    )

    print(
        "DEMO_CLONE_ACCOUNTS_0005=APPLIED"
    )

    print(
        "DEMO_CLONE_BROWSERSESSION_TABLE=PRESENT"
    )

    print(
        "MIGRATE_BEFORE_ENABLE=YES"
    )

    print(
        "PROTECTED_DB_SHA256_AFTER="
        + source_hash_after
    )

    print(
        "PROTECTED_DB_MUTATED=NO"
    )

    print(
        "REAL_PROVIDER_CALL=NONE"
    )

    print(
        "REAL_MAIL_SEND=NONE"
    )

    print(
        "REAL_MAIL_SYNC=NONE"
    )

    print(
        "REAL_AI_EXECUTION=NONE"
    )

    print(
        "PASS - DEMO-RC1 disposable clone prepared"
    )


    return target


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Prepare an isolated DEMO-RC1 SQLite clone "
            "without mutating backend/db.sqlite3."
        )
    )


    parser.add_argument(
        "--target",
        default=str(
            DEFAULT_TARGET
        ),
    )

    parser.add_argument(
        "--replace",
        action="store_true",
    )


    args = parser.parse_args()


    try:

        prepare_demo_clone(
            target=args.target,
            replace=args.replace,
        )

    except DemoCloneError as exc:

        print(
            "STOP - "
            + str(
                exc
            ),
            file=sys.stderr,
        )

        return 1


    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
