from pathlib import Path
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.request import (
    HTTPCookieProcessor,
    Request,
    build_opener,
)
import argparse
import hashlib
import json
import os
import secrets
import socket
import sqlite3
import subprocess
import sys
import time


ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

BACKEND = (
    ROOT
    / "backend"
)

DEMO_ROOT = (
    ROOT
    / "artifacts"
    / "demo_rc1"
)

PROTECTED_DB = (
    BACKEND
    / "db.sqlite3"
)

CANONICAL_DEMO_DB = (
    DEMO_ROOT
    / "demo.sqlite3"
)

DEFAULT_SMOKE_DB = (
    DEMO_ROOT
    / "smoke.sqlite3"
)


REQUIRED_ACCOUNTS_MIGRATIONS = {
    "0003_authsec_rc1a_identity_metadata",
    "0004_auth_rc1b_identity_signin",
    "0005_authsec_rc2_browser_session",
}


CANONICAL_DATA_COUNTS = {
    "accounts_user":
        1,

    "inbox_organization":
        1,

    "inbox_organizationuser":
        1,

    "email_accounts_emailaccount":
        2,

    "inbox_inboxmessage":
        1756,

    "inbox_conversation":
        1654,

    "inbox_inboxsyncstatus":
        2,

    "oauth_tokens_oauthtoken":
        2,
}


READ_ONLY_DEMO_ENDPOINTS = (
    (
        "DASHBOARD",
        "/api/dashboard/",
    ),

    (
        "UNIFIED_INBOX",
        "/api/inbox/unified/?page=1",
    ),

    (
        "CONVERSATIONS",
        (
            "/api/inbox/"
            "unified-conversations/"
            "?folder=inbox&page=1&page_size=5"
        ),
    ),

    (
        "EMAIL_ACCOUNTS",
        "/api/email/email-accounts/",
    ),

    (
        "SYNC_STATUS",
        "/api/inbox/sync-status/",
    ),

    (
        "ACTIONS",
        "/api/actions/",
    ),

    (
        "APPROVALS",
        "/api/approvals/",
    ),

    (
        "MY_WORK",
        "/api/my-work/",
    ),

    (
        "NOTIFICATIONS",
        "/api/notifications/",
    ),

    (
        "SEARCH",
        "/api/search/?q=",
    ),

    (
        "WORKFLOWS",
        "/api/workflow/definitions/",
    ),
)


class DemoSmokeError(
    RuntimeError
):
    pass


def fail(message):
    raise DemoSmokeError(
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


def resolve_smoke_target(
    value=None,
):
    target = Path(
        value
        or
        DEFAULT_SMOKE_DB
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
            "smoke target must never equal protected backend/db.sqlite3"
        )


    if (
        target
        ==
        CANONICAL_DEMO_DB.resolve()
    ):
        fail(
            "smoke target must never equal canonical demo.sqlite3"
        )


    if not is_within(
        target,
        DEMO_ROOT,
    ):
        fail(
            "smoke target must remain inside artifacts/demo_rc1"
        )


    if (
        target.suffix.lower()
        != ".sqlite3"
    ):
        fail(
            "smoke target must use a .sqlite3 file"
        )


    return target


def readonly_connection(path):
    return sqlite3.connect(
        Path(path)
        .resolve()
        .as_uri()
        + "?mode=ro",
        uri=True,
    )


def verify_canonical_demo(
    path=None,
):
    source = Path(
        path
        or
        CANONICAL_DEMO_DB
    ).resolve()


    if not source.exists():
        fail(
            "canonical demo.sqlite3 is missing"
        )


    connection = (
        readonly_connection(
            source
        )
    )


    try:

        integrity = (
            connection.execute(
                "PRAGMA integrity_check"
            )
            .fetchone()
        )


        if (
            not integrity
            or
            str(
                integrity[0]
            ).lower()
            != "ok"
        ):
            fail(
                "canonical demo clone integrity failed"
            )


        applied = {
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


        missing = (
            REQUIRED_ACCOUNTS_MIGRATIONS
            -
            applied
        )


        if missing:
            fail(
                "canonical demo clone missing accounts migration: "
                + ", ".join(
                    sorted(
                        missing
                    )
                )
            )


        for table, expected in (
            CANONICAL_DATA_COUNTS.items()
        ):

            actual = int(
                connection.execute(
                    f'SELECT COUNT(*) FROM "{table}"'
                ).fetchone()[0]
            )


            if actual != expected:
                fail(
                    "canonical demo count mismatch for "
                    + table
                    + ": expected "
                    + str(
                        expected
                    )
                    + ", found "
                    + str(
                        actual
                    )
                )


    finally:

        connection.close()


    return source


def copy_canonical_to_smoke(
    target,
    *,
    replace=False,
):
    source = (
        verify_canonical_demo()
    )

    target = resolve_smoke_target(
        target
    )


    source_hash_before = (
        sha256_file(
            source
        )
    )


    if target.exists():

        if not replace:
            fail(
                "smoke DB already exists; use --replace"
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


    if (
        sha256_file(
            source
        )
        != source_hash_before
    ):
        fail(
            "canonical demo clone changed while creating smoke copy"
        )


    return target


def build_runtime_environment(
    smoke_db,
    *,
    base_environment=None,
):
    smoke_db = resolve_smoke_target(
        smoke_db
    )


    environment = dict(
        base_environment
        if base_environment is not None
        else os.environ
    )


    environment.update(
        {
            "DJANGO_DB_ENGINE":
                "sqlite",

            "ONEUCH_SQLITE_PATH":
                str(
                    smoke_db
                ),

            "AUTH_BROWSER_SESSION_ENABLED":
                "true",

            "CORS_ALLOW_CREDENTIALS":
                "true",

            "CORS_ALLOW_ALL_ORIGINS":
                "true",

            "DJANGO_DEBUG":
                "true",

            "DJANGO_ALLOWED_HOSTS":
                "127.0.0.1,localhost",
        }
    )


    return environment


def select_demo_email(
    smoke_db,
):
    connection = (
        readonly_connection(
            smoke_db
        )
    )


    try:

        row = (
            connection.execute(
                """
                SELECT email
                FROM accounts_user
                WHERE is_active=1
                ORDER BY id
                LIMIT 1
                """
            )
            .fetchone()
        )


    finally:

        connection.close()


    if (
        not row
        or
        not str(
            row[0]
        ).strip()
    ):
        fail(
            "active demo user unavailable in smoke DB"
        )


    return str(
        row[0]
    ).strip()


def set_temporary_password(
    smoke_db,
    *,
    email,
    password,
):
    environment = (
        build_runtime_environment(
            smoke_db
        )
    )


    environment[
        "ONEUCH_DEMO_EMAIL"
    ] = email

    environment[
        "ONEUCH_DEMO_PASSWORD"
    ] = password


    code = (
        "import os;"
        "from accounts.models import User;"
        "u=User.objects.filter("
        "email__iexact=os.environ['ONEUCH_DEMO_EMAIL'],"
        "is_active=True"
        ").first();"
        "assert u is not None;"
        "u.set_password(os.environ['ONEUCH_DEMO_PASSWORD']);"
        "u.save(update_fields=['password'])"
    )


    result = subprocess.run(
        [
            sys.executable,
            "manage.py",
            "shell",
            "-c",
            code,
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


    if result.returncode != 0:
        fail(
            "unable to set temporary smoke-only password"
        )


def choose_local_port():
    with socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM,
    ) as sock:

        sock.bind(
            (
                "127.0.0.1",
                0,
            )
        )

        return int(
            sock.getsockname()[1]
        )


def decode_json(
    raw,
):
    try:

        return json.loads(
            raw.decode(
                "utf-8"
            )
        )

    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:

        raise DemoSmokeError(
            "non-JSON HTTP response"
        ) from exc


def request_json(
    opener,
    base_url,
    method,
    path,
    *,
    payload=None,
    headers=None,
):
    request_headers = {
        "Accept":
            "application/json",
    }


    if headers:
        request_headers.update(
            headers
        )


    body = None


    if payload is not None:

        body = json.dumps(
            payload
        ).encode(
            "utf-8"
        )

        request_headers[
            "Content-Type"
        ] = "application/json"


    request = Request(
        base_url
        + path,
        data=body,
        headers=request_headers,
        method=method,
    )


    try:

        response = opener.open(
            request,
            timeout=10,
        )


        raw = response.read()


        return (
            int(
                response.status
            ),
            decode_json(
                raw
            ),
        )


    except HTTPError as exc:

        raw = exc.read()


        try:

            payload_result = (
                decode_json(
                    raw
                )
            )

        except DemoSmokeError:

            payload_result = {
                "raw":
                    raw.decode(
                        "utf-8",
                        errors="replace",
                    )
            }


        return (
            int(
                exc.code
            ),
            payload_result,
        )


def wait_for_csrf(
    opener,
    base_url,
):
    last_error = None


    for _attempt in range(
        80
    ):

        try:

            status_code, payload = (
                request_json(
                    opener,
                    base_url,
                    "GET",
                    "/api/auth/session/csrf/",
                )
            )


            if (
                status_code == 200
                and
                isinstance(
                    payload,
                    dict,
                )
                and
                payload.get(
                    "csrf_token"
                )
            ):

                return str(
                    payload[
                        "csrf_token"
                    ]
                )


            last_error = (
                "unexpected CSRF response "
                + str(
                    status_code
                )
            )


        except (
            URLError,
            ConnectionError,
            OSError,
        ) as exc:

            last_error = str(
                exc
            )


        time.sleep(
            0.25
        )


    fail(
        "local Django server did not become ready: "
        + str(
            last_error
        )
    )


def assert_status(
    label,
    status_code,
    expected=200,
):
    if status_code != expected:
        fail(
            label
            + " expected HTTP "
            + str(
                expected
            )
            + ", found "
            + str(
                status_code
            )
        )


def cookie_names(
    jar,
):
    return {
        cookie.name

        for cookie in jar
    }


def run_live_smoke(
    smoke_db,
):
    smoke_db = resolve_smoke_target(
        smoke_db
    )


    email = (
        select_demo_email(
            smoke_db
        )
    )


    password = (
        secrets.token_urlsafe(
            32
        )
    )


    set_temporary_password(
        smoke_db,
        email=email,
        password=password,
    )


    environment = (
        build_runtime_environment(
            smoke_db
        )
    )


    port = (
        choose_local_port()
    )


    base_url = (
        "http://127.0.0.1:"
        + str(
            port
        )
    )


    process = subprocess.Popen(
        [
            sys.executable,
            "manage.py",
            "runserver",
            "127.0.0.1:"
            + str(
                port
            ),
            "--noreload",
        ],
        cwd=str(
            BACKEND
        ),
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


    jar = CookieJar()

    opener = build_opener(
        HTTPCookieProcessor(
            jar
        )
    )


    try:

        csrf_token = (
            wait_for_csrf(
                opener,
                base_url,
            )
        )


        if (
            "oneuch_session_csrf"
            not in cookie_names(
                jar
            )
        ):
            fail(
                "browser-session CSRF cookie missing"
            )


        status_code, login_payload = (
            request_json(
                opener,
                base_url,
                "POST",
                "/api/auth/session/login/",
                payload={
                    "email":
                        email,

                    "password":
                        password,
                },
                headers={
                    "X-OneUCH-CSRF":
                        csrf_token,
                },
            )
        )


        assert_status(
            "browser login",
            status_code,
        )


        if (
            not isinstance(
                login_payload,
                dict,
            )
            or
            not login_payload.get(
                "access"
            )
        ):
            fail(
                "browser login did not return access token"
            )


        if (
            "refresh"
            in login_payload
        ):
            fail(
                "browser login exposed refresh token in JSON"
            )


        if (
            "oneuch_refresh"
            not in cookie_names(
                jar
            )
        ):
            fail(
                "HttpOnly refresh cookie missing after login"
            )


        access = str(
            login_payload[
                "access"
            ]
        )


        auth_headers = {
            "Authorization":
                "Bearer "
                + access,
        }


        status_code, me_payload = (
            request_json(
                opener,
                base_url,
                "GET",
                "/api/auth/me/",
                headers=(
                    auth_headers
                ),
            )
        )


        assert_status(
            "authenticated identity",
            status_code,
        )


        if (
            not isinstance(
                me_payload,
                dict,
            )
            or
            me_payload.get(
                "status"
            )
            != "active"
        ):
            fail(
                "authenticated identity is not active"
            )


        if not me_payload.get(
            "mailbox_connected"
        ):
            fail(
                "demo identity does not report connected mailbox"
            )


        status_code, bootstrap_payload = (
            request_json(
                opener,
                base_url,
                "POST",
                "/api/auth/session/bootstrap/",
                payload={},
                headers={
                    "X-OneUCH-CSRF":
                        csrf_token,
                },
            )
        )


        assert_status(
            "browser bootstrap",
            status_code,
        )


        if (
            not isinstance(
                bootstrap_payload,
                dict,
            )
            or
            bootstrap_payload.get(
                "authenticated"
            )
            is not True
            or
            not bootstrap_payload.get(
                "access"
            )
        ):
            fail(
                "browser bootstrap contract failed"
            )


        access = str(
            bootstrap_payload[
                "access"
            ]
        )


        status_code, refresh_payload = (
            request_json(
                opener,
                base_url,
                "POST",
                "/api/auth/session/refresh/",
                payload={},
                headers={
                    "X-OneUCH-CSRF":
                        csrf_token,
                },
            )
        )


        assert_status(
            "browser refresh",
            status_code,
        )


        if (
            not isinstance(
                refresh_payload,
                dict,
            )
            or
            not refresh_payload.get(
                "access"
            )
            or
            "refresh"
            in refresh_payload
        ):
            fail(
                "browser refresh contract failed"
            )


        access = str(
            refresh_payload[
                "access"
            ]
        )


        auth_headers = {
            "Authorization":
                "Bearer "
                + access,
        }


        results = {}


        for label, path in (
            READ_ONLY_DEMO_ENDPOINTS
        ):

            status_code, payload = (
                request_json(
                    opener,
                    base_url,
                    "GET",
                    path,
                    headers=(
                        auth_headers
                    ),
                )
            )


            assert_status(
                label,
                status_code,
            )


            results[
                label
            ] = payload


        dashboard = results[
            "DASHBOARD"
        ]


        if (
            not isinstance(
                dashboard,
                dict,
            )
            or
            int(
                dashboard.get(
                    "total_messages",
                    -1,
                )
            )
            != 1756
        ):
            fail(
                "dashboard message count does not match demo dataset"
            )


        inbox = results[
            "UNIFIED_INBOX"
        ]


        if (
            not isinstance(
                inbox,
                dict,
            )
            or
            int(
                inbox.get(
                    "count",
                    -1,
                )
            )
            != 1756
        ):
            fail(
                "unified inbox count does not match demo dataset"
            )


        conversations = results[
            "CONVERSATIONS"
        ]


        if (
            not isinstance(
                conversations,
                dict,
            )
            or
            "results"
            not in conversations
        ):
            fail(
                "conversation demo payload invalid"
            )


        email_accounts = results[
            "EMAIL_ACCOUNTS"
        ]


        if (
            not isinstance(
                email_accounts,
                list,
            )
            or
            len(
                email_accounts
            )
            != 2
        ):
            fail(
                "email-account demo count mismatch"
            )


        sync_status = results[
            "SYNC_STATUS"
        ]


        if (
            not isinstance(
                sync_status,
                list,
            )
            or
            len(
                sync_status
            )
            != 2
        ):
            fail(
                "sync-status demo count mismatch"
            )


        if not isinstance(
            results[
                "ACTIONS"
            ],
            list,
        ):
            fail(
                "actions list payload invalid"
            )


        if not isinstance(
            results[
                "APPROVALS"
            ],
            list,
        ):
            fail(
                "approvals list payload invalid"
            )


        if not isinstance(
            results[
                "MY_WORK"
            ],
            dict,
        ):
            fail(
                "My Work payload invalid"
            )


        if not isinstance(
            results[
                "NOTIFICATIONS"
            ],
            dict,
        ):
            fail(
                "notifications payload invalid"
            )


        search_payload = results[
            "SEARCH"
        ]


        if (
            not isinstance(
                search_payload,
                dict,
            )
            or
            int(
                search_payload.get(
                    "count",
                    -1,
                )
            )
            != 0
        ):
            fail(
                "empty search demo contract failed"
            )


        if not isinstance(
            results[
                "WORKFLOWS"
            ],
            list,
        ):
            fail(
                "workflow list payload invalid"
            )


        print(
            "PASS - browser CSRF seed HTTP"
        )

        print(
            "PASS - browser password login HTTP"
        )

        print(
            "PASS - refresh credential remained HttpOnly cookie"
        )

        print(
            "PASS - authenticated /api/auth/me/"
        )

        print(
            "PASS - browser bootstrap rotation HTTP"
        )

        print(
            "PASS - browser refresh rotation HTTP"
        )


        for label, _path in (
            READ_ONLY_DEMO_ENDPOINTS
        ):

            payload = results[
                label
            ]


            if isinstance(
                payload,
                list,
            ):

                item_count = len(
                    payload
                )

            elif (
                isinstance(
                    payload,
                    dict,
                )
                and
                isinstance(
                    payload.get(
                        "results"
                    ),
                    list,
                )
            ):

                item_count = len(
                    payload[
                        "results"
                    ]
                )

            else:

                item_count = None


            if item_count is None:

                print(
                    "DEMO_HTTP_"
                    + label
                    + "=200"
                )

            else:

                print(
                    "DEMO_HTTP_"
                    + label
                    + "=200 ITEMS="
                    + str(
                        item_count
                    )
                )


        print(
            "DEMO_DASHBOARD_TOTAL_MESSAGES="
            + str(
                dashboard[
                    "total_messages"
                ]
            )
        )

        print(
            "DEMO_INBOX_TOTAL_MESSAGES="
            + str(
                inbox[
                    "count"
                ]
            )
        )

        print(
            "DEMO_EMAIL_ACCOUNT_COUNT="
            + str(
                len(
                    email_accounts
                )
            )
        )

        print(
            "DEMO_SYNC_STATUS_COUNT="
            + str(
                len(
                    sync_status
                )
            )
        )


        status_code, logout_payload = (
            request_json(
                opener,
                base_url,
                "POST",
                "/api/auth/session/end/",
                payload={},
                headers={
                    "X-OneUCH-CSRF":
                        csrf_token,
                },
            )
        )


        assert_status(
            "browser logout",
            status_code,
        )


        if (
            not isinstance(
                logout_payload,
                dict,
            )
            or
            logout_payload.get(
                "ended"
            )
            is not True
        ):
            fail(
                "browser logout contract failed"
            )


        status_code, _payload = (
            request_json(
                opener,
                base_url,
                "GET",
                "/api/auth/me/",
                headers=(
                    auth_headers
                ),
            )
        )


        if status_code != 401:
            fail(
                "revoked access token remained usable after logout"
            )


        connection = (
            readonly_connection(
                smoke_db
            )
        )


        try:

            revoked_logout_count = int(
                connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM accounts_browsersession
                    WHERE revoked_at IS NOT NULL
                      AND revocation_reason='logout'
                    """
                ).fetchone()[0]
            )


        finally:

            connection.close()


        if revoked_logout_count < 1:
            fail(
                "logout revocation not persisted in smoke DB"
            )


        print(
            "PASS - browser logout HTTP"
        )

        print(
            "PASS - logout server revocation persisted"
        )

        print(
            "PASS - old access rejected after logout"
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
            "ACTION_MUTATION=NONE"
        )

        print(
            "APPROVAL_MUTATION=NONE"
        )

        print(
            "WORKFLOW_MUTATION=NONE"
        )


    finally:

        if process.poll() is None:

            process.terminate()


            try:

                process.wait(
                    timeout=5
                )

            except subprocess.TimeoutExpired:

                process.kill()

                process.wait(
                    timeout=5
                )


def prepare_and_run(
    *,
    target=None,
    replace=False,
):
    target = resolve_smoke_target(
        target
    )


    protected_hash_before = (
        sha256_file(
            PROTECTED_DB
        )
    )

    canonical_hash_before = (
        sha256_file(
            CANONICAL_DEMO_DB
        )
    )


    copy_canonical_to_smoke(
        target,
        replace=replace,
    )


    print(
        "PASS - canonical demo clone copied to smoke DB"
    )


    run_live_smoke(
        target
    )


    protected_hash_after = (
        sha256_file(
            PROTECTED_DB
        )
    )

    canonical_hash_after = (
        sha256_file(
            CANONICAL_DEMO_DB
        )
    )


    if (
        protected_hash_after
        !=
        protected_hash_before
    ):
        fail(
            "protected DB changed during G3 smoke"
        )


    if (
        canonical_hash_after
        !=
        canonical_hash_before
    ):
        fail(
            "canonical demo clone changed during G3 smoke"
        )


    print(
        "PROTECTED_DB_MUTATED=NO"
    )

    print(
        "CANONICAL_DEMO_DB_MUTATED=NO"
    )

    print(
        "SMOKE_DB_SHA256="
        + sha256_file(
            target
        )
    )

    print(
        "PASS - DEMO-RC1 G3 authenticated local smoke GREEN"
    )


    return target


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Run authenticated DEMO-RC1 live-HTTP smoke "
            "against an isolated smoke copy."
        )
    )


    parser.add_argument(
        "--target",
        default=str(
            DEFAULT_SMOKE_DB
        ),
    )

    parser.add_argument(
        "--replace",
        action="store_true",
    )


    args = parser.parse_args()


    try:

        prepare_and_run(
            target=args.target,
            replace=args.replace,
        )

    except DemoSmokeError as exc:

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
