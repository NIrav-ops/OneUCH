from pathlib import Path
from http.cookiejar import CookieJar
from urllib.request import (
    HTTPCookieProcessor,
    build_opener,
)
import argparse
import secrets
import sqlite3
import subprocess
import sys


import demo_rc1_smoke as smoke


ROOT = smoke.ROOT
BACKEND = smoke.BACKEND

PROTECTED_DB = smoke.PROTECTED_DB
CANONICAL_DEMO_DB = smoke.CANONICAL_DEMO_DB

DEMO_ROOT = smoke.DEMO_ROOT

DEFAULT_STORY_DB = (
    DEMO_ROOT
    / "story.sqlite3"
)


FIXTURE_PREFIX = (
    "[DEMO-RC1]"
)

DEMO_WORKFLOW_CODE = (
    "demo_rc1_customer_delivery"
)


EXPECTED_STORY_COUNTS = {
    "actions":
        2,

    "approvals":
        2,

    "workflows":
        1,

    "workflow_nodes":
        4,

    "workflow_transitions":
        3,

    "my_work":
        4,
}


EXPECTED_WORKFLOW_NODE_TYPES = {
    "start",
    "approval",
    "action",
    "end",
}


STORY_READ_ENDPOINTS = {
    "actions":
        "/api/actions/",

    "approvals":
        "/api/approvals/",

    "my_work":
        "/api/my-work/",

    "workflows":
        "/api/workflow/definitions/",

    "dashboard":
        "/api/dashboard/",

    "inbox":
        "/api/inbox/unified/?page=1",
}


class DemoStoryError(
    RuntimeError
):
    pass


def fail(message):
    raise DemoStoryError(
        message
    )


def resolve_story_target(
    value=None,
):
    target = (
        smoke.resolve_smoke_target(
            value
            or
            DEFAULT_STORY_DB
        )
    )


    if (
        target
        ==
        smoke.DEFAULT_SMOKE_DB.resolve()
    ):
        fail(
            "story target must not overwrite G3 smoke.sqlite3"
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


SEED_CODE = r"""
from datetime import timedelta

from django.utils import timezone

from inbox.models import (
    InboxMessage,
    OrganizationUser,
)

from actions.models import (
    ActionItem,
)

from approvals.models import (
    ApprovalItem,
)

from workflow.models import (
    WorkflowDefinition,
    WorkflowNode,
    WorkflowTransition,
)


FIXTURE_PREFIX = "[DEMO-RC1]"
WORKFLOW_CODE = "demo_rc1_customer_delivery"


membership = (
    OrganizationUser.objects
    .select_related(
        "user",
        "organization",
    )
    .filter(
        user__is_active=True,
        organization__is_active=True,
    )
    .order_by(
        "id"
    )
    .first()
)


assert membership is not None, (
    "active demo membership missing"
)


user = membership.user
organization = membership.organization


messages = list(
    InboxMessage.objects
    .filter(
        user=user,
        organization=organization,
        conversation__isnull=False,
    )
    .select_related(
        "conversation"
    )
    .order_by(
        "-received_at",
        "-id",
    )[:2]
)


assert len(messages) >= 2, (
    "at least two communication-backed messages required"
)


message_one = messages[0]
message_two = messages[1]


ActionItem.objects.filter(
    user=user,
    organization=organization,
    title__startswith=FIXTURE_PREFIX,
).delete()


ApprovalItem.objects.filter(
    user=user,
    organization=organization,
    title__startswith=FIXTURE_PREFIX,
).delete()


WorkflowDefinition.objects.filter(
    organization=organization,
    code=WORKFLOW_CODE,
).delete()


now = timezone.now()


approval_one = (
    ApprovalItem.objects.create(
        user=user,
        organization=organization,
        message=message_one,
        conversation=message_one.conversation,
        title=(
            "[DEMO-RC1] Approve migration cutover plan"
        ),
        description=(
            "Governed approval required before "
            "the customer delivery team proceeds "
            "with the migration cutover."
        ),
        requested_by=(
            "demo.stakeholder@example.com"
        ),
        assigned_to=user,
        status="pending",
        source_type="email",
        due_date=(
            now
            + timedelta(
                days=2
            )
        ),
        confidence_score=100,
        priority=85,
        approval_analyzed=True,
        action_created=True,
    )
)


approval_two = (
    ApprovalItem.objects.create(
        user=user,
        organization=organization,
        message=message_two,
        conversation=message_two.conversation,
        title=(
            "[DEMO-RC1] Confirm commercial exception"
        ),
        description=(
            "Review the requested commercial exception "
            "and provide the missing decision context."
        ),
        requested_by=(
            "demo.finance@example.com"
        ),
        assigned_to=user,
        status="needs_info",
        source_type="email",
        due_date=(
            now
            + timedelta(
                days=4
            )
        ),
        confidence_score=100,
        priority=65,
        approval_analyzed=True,
    )
)


action_one = (
    ActionItem.objects.create(
        user=user,
        organization=organization,
        message=message_one,
        title=(
            "[DEMO-RC1] Confirm migration scope and owners"
        ),
        description=(
            "Review the communication context and "
            "confirm the delivery scope, owner and "
            "next customer milestone."
        ),
        owner=user,
        due_date=(
            now
            + timedelta(
                days=1
            )
        ),
        priority=90,
        status="in_progress",
        source_type="email",
        confidence_score=100,
    )
)


action_two = (
    ActionItem.objects.create(
        user=user,
        organization=organization,
        message=message_two,
        source_approval=approval_one,
        title=(
            "[DEMO-RC1] Send approved implementation timeline"
        ),
        description=(
            "Translate the governed approval into "
            "an owned customer execution step."
        ),
        owner=user,
        due_date=(
            now
            + timedelta(
                days=3
            )
        ),
        priority=75,
        status="open",
        source_type="approval",
        confidence_score=100,
    )
)


workflow = (
    WorkflowDefinition.objects.create(
        organization=organization,
        name=(
            "Customer Delivery Approval"
        ),
        code=WORKFLOW_CODE,
        description=(
            "Demo workflow connecting communication, "
            "approval governance and owned execution."
        ),
        version=1,
        status=(
            WorkflowDefinition.STATUS_ACTIVE
        ),
        created_by=user,
    )
)


start_node = (
    WorkflowNode.objects.create(
        workflow=workflow,
        name="Communication received",
        node_type=(
            WorkflowNode.START
        ),
        configuration={
            "demo_only":
                True,
        },
        position_x=80,
        position_y=120,
    )
)


approval_node = (
    WorkflowNode.objects.create(
        workflow=workflow,
        name="Approval gate",
        node_type=(
            WorkflowNode.APPROVAL
        ),
        configuration={
            "demo_only":
                True,

            "purpose":
                "Govern customer delivery decision",
        },
        position_x=320,
        position_y=120,
    )
)


action_node = (
    WorkflowNode.objects.create(
        workflow=workflow,
        name="Owned execution",
        node_type=(
            WorkflowNode.ACTION
        ),
        configuration={
            "demo_only":
                True,

            "purpose":
                "Convert approval into owned work",
        },
        position_x=560,
        position_y=120,
    )
)


end_node = (
    WorkflowNode.objects.create(
        workflow=workflow,
        name="Delivery checkpoint complete",
        node_type=(
            WorkflowNode.END
        ),
        configuration={
            "demo_only":
                True,
        },
        position_x=800,
        position_y=120,
    )
)


WorkflowTransition.objects.create(
    workflow=workflow,
    source=start_node,
    target=approval_node,
    priority=10,
)


WorkflowTransition.objects.create(
    workflow=workflow,
    source=approval_node,
    target=action_node,
    priority=20,
)


WorkflowTransition.objects.create(
    workflow=workflow,
    source=action_node,
    target=end_node,
    priority=30,
)


assert (
    ActionItem.objects.filter(
        user=user,
        organization=organization,
        title__startswith=FIXTURE_PREFIX,
    ).count()
    ==
    2
)


assert (
    ApprovalItem.objects.filter(
        user=user,
        organization=organization,
        title__startswith=FIXTURE_PREFIX,
    ).count()
    ==
    2
)


assert (
    WorkflowDefinition.objects.filter(
        organization=organization,
        code=WORKFLOW_CODE,
    ).count()
    ==
    1
)


assert workflow.nodes.count() == 4
assert workflow.transitions.count() == 3


print(
    "STORY_SEED_ACTIONS=2"
)

print(
    "STORY_SEED_APPROVALS=2"
)

print(
    "STORY_SEED_WORKFLOWS=1"
)

print(
    "STORY_SEED_WORKFLOW_NODES=4"
)

print(
    "STORY_SEED_WORKFLOW_TRANSITIONS=3"
)
"""


def copy_canonical_to_story(
    target,
    *,
    replace=False,
):
    target = resolve_story_target(
        target
    )


    return (
        smoke.copy_canonical_to_smoke(
            target,
            replace=replace,
        )
    )


def seed_story(
    target,
):
    target = resolve_story_target(
        target
    )


    environment = (
        smoke.build_runtime_environment(
            target
        )
    )


    result = subprocess.run(
        [
            sys.executable,
            "manage.py",
            "shell",
            "-c",
            SEED_CODE,
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
            "story fixture seed failed"
        )


def verify_story_database(
    target,
):
    target = resolve_story_target(
        target
    )


    connection = (
        readonly_connection(
            target
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
                "story SQLite integrity RED"
            )


        actions = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM actions_actionitem
                WHERE title LIKE '[DEMO-RC1]%'
                """
            ).fetchone()[0]
        )


        approvals = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM approvals_approvalitem
                WHERE title LIKE '[DEMO-RC1]%'
                """
            ).fetchone()[0]
        )


        workflow_row = (
            connection.execute(
                """
                SELECT id
                FROM workflow_workflowdefinition
                WHERE code=?
                """,
                (
                    DEMO_WORKFLOW_CODE,
                ),
            ).fetchone()
        )


        if workflow_row is None:
            fail(
                "demo workflow definition missing"
            )


        workflow_id = (
            workflow_row[0]
        )


        workflows = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM workflow_workflowdefinition
                WHERE code=?
                """,
                (
                    DEMO_WORKFLOW_CODE,
                ),
            ).fetchone()[0]
        )


        nodes = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM workflow_workflownode
                WHERE workflow_id=?
                """,
                (
                    workflow_id,
                ),
            ).fetchone()[0]
        )


        transitions = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM workflow_workflowtransition
                WHERE workflow_id=?
                """,
                (
                    workflow_id,
                ),
            ).fetchone()[0]
        )


        communication_backed_actions = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM actions_actionitem
                WHERE title LIKE '[DEMO-RC1]%'
                  AND message_id IS NOT NULL
                """
            ).fetchone()[0]
        )


        communication_backed_approvals = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM approvals_approvalitem
                WHERE title LIKE '[DEMO-RC1]%'
                  AND message_id IS NOT NULL
                  AND conversation_id IS NOT NULL
                """
            ).fetchone()[0]
        )


    finally:

        connection.close()


    counts = {
        "actions":
            actions,

        "approvals":
            approvals,

        "workflows":
            workflows,

        "workflow_nodes":
            nodes,

        "workflow_transitions":
            transitions,
    }


    for label in (
        "actions",
        "approvals",
        "workflows",
        "workflow_nodes",
        "workflow_transitions",
    ):

        expected = (
            EXPECTED_STORY_COUNTS[
                label
            ]
        )

        actual = counts[
            label
        ]


        if actual != expected:
            fail(
                "story count mismatch for "
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


    if communication_backed_actions != 2:
        fail(
            "both demo Actions must remain communication-backed"
        )


    if communication_backed_approvals != 2:
        fail(
            "both demo Approvals must remain communication-backed"
        )


    print(
        "STORY_DB_ACTIONS=2"
    )

    print(
        "STORY_DB_APPROVALS=2"
    )

    print(
        "STORY_DB_WORKFLOWS=1"
    )

    print(
        "STORY_DB_WORKFLOW_NODES=4"
    )

    print(
        "STORY_DB_WORKFLOW_TRANSITIONS=3"
    )

    print(
        "STORY_DB_COMMUNICATION_BACKED_ACTIONS=2"
    )

    print(
        "STORY_DB_COMMUNICATION_BACKED_APPROVALS=2"
    )


    return counts


def run_story_http(
    target,
):
    target = resolve_story_target(
        target
    )


    email = (
        smoke.select_demo_email(
            target
        )
    )


    password = (
        secrets.token_urlsafe(
            32
        )
    )


    smoke.set_temporary_password(
        target,
        email=email,
        password=password,
    )


    environment = (
        smoke.build_runtime_environment(
            target
        )
    )


    port = (
        smoke.choose_local_port()
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
            smoke.wait_for_csrf(
                opener,
                base_url,
            )
        )


        status_code, login_payload = (
            smoke.request_json(
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


        smoke.assert_status(
            "story login",
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
            or
            "refresh"
            in login_payload
        ):
            fail(
                "story browser-login contract failed"
            )


        if (
            "oneuch_refresh"
            not in smoke.cookie_names(
                jar
            )
        ):
            fail(
                "story refresh cookie missing"
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
            smoke.request_json(
                opener,
                base_url,
                "GET",
                "/api/auth/me/",
                headers=auth_headers,
            )
        )


        smoke.assert_status(
            "story authenticated identity",
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
                "story identity is not active"
            )


        status_code, bootstrap_payload = (
            smoke.request_json(
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


        smoke.assert_status(
            "story bootstrap",
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
                "story bootstrap contract failed"
            )


        status_code, refresh_payload = (
            smoke.request_json(
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


        smoke.assert_status(
            "story refresh",
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
                "story refresh contract failed"
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


        payloads = {}


        for label, path in (
            STORY_READ_ENDPOINTS.items()
        ):

            status_code, payload = (
                smoke.request_json(
                    opener,
                    base_url,
                    "GET",
                    path,
                    headers=auth_headers,
                )
            )


            smoke.assert_status(
                "story "
                + label,
                status_code,
            )


            payloads[
                label
            ] = payload


        actions = payloads[
            "actions"
        ]

        approvals = payloads[
            "approvals"
        ]

        my_work = payloads[
            "my_work"
        ]

        workflows = payloads[
            "workflows"
        ]

        dashboard = payloads[
            "dashboard"
        ]

        inbox = payloads[
            "inbox"
        ]


        if (
            not isinstance(
                actions,
                list,
            )
            or
            len(
                actions
            )
            != 2
        ):
            fail(
                "authenticated Actions story count must equal 2"
            )


        if (
            not all(
                str(
                    item.get(
                        "title",
                        ""
                    )
                ).startswith(
                    FIXTURE_PREFIX
                )

                for item
                in actions
            )
        ):
            fail(
                "authenticated Actions payload contains non-demo item"
            )


        if (
            not isinstance(
                approvals,
                list,
            )
            or
            len(
                approvals
            )
            != 2
        ):
            fail(
                "authenticated Approvals story count must equal 2"
            )


        if (
            not all(
                str(
                    item.get(
                        "title",
                        ""
                    )
                ).startswith(
                    FIXTURE_PREFIX
                )

                for item
                in approvals
            )
        ):
            fail(
                "authenticated Approvals payload contains non-demo item"
            )


        if (
            not isinstance(
                workflows,
                list,
            )
            or
            len(
                workflows
            )
            != 1
        ):
            fail(
                "authenticated Workflow story count must equal 1"
            )


        workflow = (
            workflows[0]
        )


        if (
            workflow.get(
                "code"
            )
            != DEMO_WORKFLOW_CODE
            or
            workflow.get(
                "status"
            )
            != "active"
        ):
            fail(
                "demo Workflow list contract failed"
            )


        workflow_id = str(
            workflow[
                "id"
            ]
        )


        if not isinstance(
            my_work,
            dict,
        ):
            fail(
                "My Work story payload invalid"
            )


        summary = (
            my_work.get(
                "summary"
            )
            or
            {}
        )


        items = (
            my_work.get(
                "items"
            )
            or
            []
        )


        if int(
            summary.get(
                "total",
                -1,
            )
        ) != 4:
            fail(
                "My Work total must equal 4"
            )


        if int(
            summary.get(
                "actions",
                -1,
            )
        ) != 2:
            fail(
                "My Work Actions must equal 2"
            )


        if int(
            summary.get(
                "approvals",
                -1,
            )
        ) != 2:
            fail(
                "My Work Approvals must equal 2"
            )


        if len(
            items
        ) != 4:
            fail(
                "My Work items must equal 4"
            )


        if not all(
            item.get(
                "open_url"
            )

            for item
            in items
        ):
            fail(
                "every My Work fixture must remain communication-linked"
            )


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
                "story copy lost canonical dashboard message count"
            )


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
                "story copy lost canonical inbox message count"
            )


        status_code, detail = (
            smoke.request_json(
                opener,
                base_url,
                "GET",
                (
                    "/api/workflow/definitions/"
                    + workflow_id
                    + "/"
                ),
                headers=auth_headers,
            )
        )


        smoke.assert_status(
            "story workflow detail",
            status_code,
        )


        if (
            not isinstance(
                detail,
                dict,
            )
            or
            detail.get(
                "code"
            )
            != DEMO_WORKFLOW_CODE
        ):
            fail(
                "workflow detail story contract failed"
            )


        status_code, graph = (
            smoke.request_json(
                opener,
                base_url,
                "GET",
                (
                    "/api/workflow/builder/graph/"
                    "?workflow="
                    + workflow_id
                ),
                headers=auth_headers,
            )
        )


        smoke.assert_status(
            "story workflow graph",
            status_code,
        )


        graph_nodes = (
            graph.get(
                "nodes"
            )
            if isinstance(
                graph,
                dict,
            )
            else None
        )


        graph_transitions = (
            graph.get(
                "transitions"
            )
            if isinstance(
                graph,
                dict,
            )
            else None
        )


        if (
            not isinstance(
                graph_nodes,
                list,
            )
            or
            len(
                graph_nodes
            )
            != 4
        ):
            fail(
                "workflow graph must expose four nodes"
            )


        if (
            not isinstance(
                graph_transitions,
                list,
            )
            or
            len(
                graph_transitions
            )
            != 3
        ):
            fail(
                "workflow graph must expose three transitions"
            )


        actual_node_types = {
            str(
                node.get(
                    "node_type"
                )
            )

            for node
            in graph_nodes
        }


        if (
            actual_node_types
            !=
            EXPECTED_WORKFLOW_NODE_TYPES
        ):
            fail(
                "workflow graph node-type contract mismatch"
            )


        print(
            "STORY_HTTP_AUTH=GREEN"
        )

        print(
            "STORY_HTTP_ACTIONS=200 ITEMS=2"
        )

        print(
            "STORY_HTTP_APPROVALS=200 ITEMS=2"
        )

        print(
            "STORY_HTTP_WORKFLOWS=200 ITEMS=1"
        )

        print(
            "STORY_HTTP_MY_WORK=200 ITEMS=4"
        )

        print(
            "STORY_HTTP_MY_WORK_ACTIONS=2"
        )

        print(
            "STORY_HTTP_MY_WORK_APPROVALS=2"
        )

        print(
            "STORY_HTTP_WORKFLOW_DETAIL=200"
        )

        print(
            "STORY_HTTP_WORKFLOW_GRAPH=200"
        )

        print(
            "STORY_HTTP_WORKFLOW_GRAPH_NODES=4"
        )

        print(
            "STORY_HTTP_WORKFLOW_GRAPH_TRANSITIONS=3"
        )

        print(
            "STORY_HTTP_DASHBOARD_MESSAGES=1756"
        )

        print(
            "STORY_HTTP_INBOX_MESSAGES=1756"
        )


        status_code, logout_payload = (
            smoke.request_json(
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


        smoke.assert_status(
            "story logout",
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
                "story logout contract failed"
            )


        status_code, _payload = (
            smoke.request_json(
                opener,
                base_url,
                "GET",
                "/api/auth/me/",
                headers=auth_headers,
            )
        )


        if status_code != 401:
            fail(
                "story access remained usable after logout"
            )


        connection = (
            readonly_connection(
                target
            )
        )


        try:

            logout_count = int(
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


        if logout_count < 1:
            fail(
                "story logout revocation missing"
            )


        print(
            "STORY_HTTP_LOGOUT=GREEN"
        )

        print(
            "STORY_HTTP_OLD_ACCESS=REJECTED"
        )

        print(
            "STORY_LOGOUT_SERVER_REVOCATION=GREEN"
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


def prepare_story(
    *,
    target=None,
    replace=False,
):
    target = resolve_story_target(
        target
    )


    protected_hash_before = (
        smoke.sha256_file(
            PROTECTED_DB
        )
    )


    canonical_hash_before = (
        smoke.sha256_file(
            CANONICAL_DEMO_DB
        )
    )


    copy_canonical_to_story(
        target,
        replace=replace,
    )


    print(
        "PASS - canonical demo copied to isolated story DB"
    )


    seed_story(
        target
    )


    verify_story_database(
        target
    )


    run_story_http(
        target
    )


    if (
        smoke.sha256_file(
            PROTECTED_DB
        )
        != protected_hash_before
    ):
        fail(
            "protected main changed during story preparation"
        )


    if (
        smoke.sha256_file(
            CANONICAL_DEMO_DB
        )
        != canonical_hash_before
    ):
        fail(
            "canonical demo changed during story preparation"
        )


    print(
        "PROTECTED_MAIN_MUTATED=NO"
    )

    print(
        "CANONICAL_DEMO_MUTATED=NO"
    )

    print(
        "STORY_DB_SHA256="
        + smoke.sha256_file(
            target
        )
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
        "PASS - DEMO-RC1 G4B POPULATED STORY GREEN"
    )


    return target


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Build an isolated communication-backed "
            "DEMO-RC1 story database and prove it "
            "through authenticated local HTTP."
        )
    )


    parser.add_argument(
        "--target",
        default=str(
            DEFAULT_STORY_DB
        ),
    )


    parser.add_argument(
        "--replace",
        action="store_true",
    )


    args = parser.parse_args()


    try:

        prepare_story(
            target=args.target,
            replace=args.replace,
        )

    except (
        DemoStoryError,
        smoke.DemoSmokeError,
    ) as exc:

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
