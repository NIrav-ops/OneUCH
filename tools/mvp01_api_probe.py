from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
OUTPUT_DIR = ROOT / "artifacts" / "mvp01"

sys.path.insert(0, str(BACKEND))

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "backend.settings",
)

import django

django.setup()

from django.urls import URLPattern, URLResolver, get_resolver


def normalize_route(prefix: str, route: str) -> str:
    value = f"{prefix}{route}"

    value = value.replace("^", "")
    value = value.replace("$", "")

    if not value.startswith("/"):
        value = "/" + value

    return value


def class_names(classes) -> list[str]:
    result = []

    for item in classes or []:
        name = getattr(item, "__name__", None)

        if name:
            result.append(name)
        else:
            result.append(str(item))

    return sorted(set(result))


def inspect_callback(pattern: URLPattern) -> dict:
    callback = pattern.callback

    view_class = getattr(
        callback,
        "view_class",
        None,
    )

    if view_class is None:
        view_class = getattr(
            callback,
            "cls",
            None,
        )

    if view_class is None:
        return {
            "view": getattr(
                callback,
                "__name__",
                str(callback),
            ),
            "view_module": getattr(
                callback,
                "__module__",
                "",
            ),
            "permissions": [],
            "authentication": [],
            "http_methods": [],
        }

    permissions = class_names(
        getattr(
            view_class,
            "permission_classes",
            [],
        )
    )

    authentication = class_names(
        getattr(
            view_class,
            "authentication_classes",
            [],
        )
    )

    http_method_names = getattr(
        view_class,
        "http_method_names",
        [],
    )

    return {
        "view": view_class.__name__,
        "view_module": getattr(
            view_class,
            "__module__",
            "",
        ),
        "permissions": permissions,
        "authentication": authentication,
        "http_methods": [
            method.upper()
            for method in http_method_names
            if method
        ],
    }


def classify_access(
    permissions: list[str],
) -> str:
    permission_set = set(permissions)

    if "AllowAny" in permission_set:
        return "PUBLIC_REVIEW_REQUIRED"

    if (
        "IsAuthenticated" in permission_set
        or "IsAdminUser" in permission_set
    ):
        return "AUTHENTICATED"

    if permissions:
        return "CUSTOM_PERMISSION"

    return "DEFAULT_PERMISSION_OR_UNDECLARED"


def walk_patterns(
    patterns,
    prefix: str = "",
) -> list[dict]:
    results = []

    for pattern in patterns:

        route = str(pattern.pattern)

        if isinstance(
            pattern,
            URLResolver,
        ):
            results.extend(
                walk_patterns(
                    pattern.url_patterns,
                    prefix=f"{prefix}{route}",
                )
            )
            continue

        if not isinstance(
            pattern,
            URLPattern,
        ):
            continue

        details = inspect_callback(
            pattern
        )

        endpoint = {
            "route": normalize_route(
                prefix,
                route,
            ),
            "name": pattern.name,
            **details,
        }

        endpoint["access_classification"] = (
            classify_access(
                endpoint["permissions"]
            )
        )

        results.append(endpoint)

    return results


def is_api_route(route: str) -> bool:
    return (
        route.startswith("/api/")
        or route == "/api"
    )


def capability_for_route(
    route: str,
) -> str:

    mappings = [
        ("/api/auth/", "Authentication"),
        ("/api/inbox/", "Inbox"),
        ("/api/email/", "Email Accounts"),
        ("/api/conversations/", "Conversations"),
        ("/api/google/", "Gmail"),
        ("/api/microsoft/", "Microsoft"),
        ("/api/actions/", "Actions"),
        ("/api/approvals/", "Approvals"),
        ("/api/knowledge/", "Knowledge"),
        ("/api/context/", "Context"),
        ("/api/timeline/", "Timeline"),
        ("/api/notifications/", "Notifications"),
        ("/api/search/", "Search"),
        ("/api/workflow/", "Workflow"),
        ("/api/audit/", "Audit"),
        ("/api/platform/", "Platform"),
        ("/api/ai/", "AI"),
    ]

    for prefix, capability in mappings:
        if route.startswith(prefix):
            return capability

    return "Other"


def create_summary(
    endpoints: list[dict],
) -> dict:

    access = {}
    capability = {}

    for endpoint in endpoints:

        access_key = endpoint[
            "access_classification"
        ]

        access[access_key] = (
            access.get(
                access_key,
                0,
            )
            + 1
        )

        capability_key = capability_for_route(
            endpoint["route"]
        )

        capability[
            capability_key
        ] = (
            capability.get(
                capability_key,
                0,
            )
            + 1
        )

    return {
        "total_api_endpoints": len(
            endpoints
        ),
        "access_classification": dict(
            sorted(
                access.items()
            )
        ),
        "capability_endpoint_counts": dict(
            sorted(
                capability.items()
            )
        ),
    }


def markdown_report(
    data: dict,
) -> str:

    summary = data["summary"]
    endpoints = data["endpoints"]

    lines = [
        "# One UCH — MVP-01 API / Governance Probe",
        "",
        f"Generated: `{data['generated_at']}`",
        "",
        "## Summary",
        "",
        (
            f"- API endpoints discovered: "
            f"`{summary['total_api_endpoints']}`"
        ),
        "",
        "## Capability Coverage",
        "",
        "| Capability | Endpoint Count |",
        "|---|---:|",
    ]

    for capability, count in (
        summary[
            "capability_endpoint_counts"
        ].items()
    ):
        lines.append(
            f"| {capability} | {count} |"
        )

    lines.extend(
        [
            "",
            "## Access Classification",
            "",
            "| Access | Count |",
            "|---|---:|",
        ]
    )

    for access, count in (
        summary[
            "access_classification"
        ].items()
    ):
        lines.append(
            f"| {access} | {count} |"
        )

    lines.extend(
        [
            "",
            "## Endpoints",
            "",
            "| Route | View | Permission | Classification |",
            "|---|---|---|---|",
        ]
    )

    for endpoint in endpoints:

        permissions = (
            ", ".join(
                endpoint["permissions"]
            )
            or "-"
        )

        lines.append(
            f"| `{endpoint['route']}` "
            f"| `{endpoint['view']}` "
            f"| {permissions} "
            f"| {endpoint['access_classification']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `AUTHENTICATED` — explicit authenticated access detected.",
            "- `CUSTOM_PERMISSION` — endpoint has custom permission logic requiring review.",
            "- `PUBLIC_REVIEW_REQUIRED` — `AllowAny` detected; validate that public access is intentional.",
            "- `DEFAULT_PERMISSION_OR_UNDECLARED` — view does not explicitly declare permissions; project-level DRF defaults must be verified.",
            "",
            "This probe performs no HTTP requests and no database writes.",
            "",
        ]
    )

    return "\n".join(lines)


def main() -> None:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    all_patterns = get_resolver().url_patterns

    endpoints = [
        endpoint
        for endpoint in walk_patterns(
            all_patterns
        )
        if is_api_route(
            endpoint["route"]
        )
    ]

    endpoints.sort(
        key=lambda item: item[
            "route"
        ]
    )

    data = {
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "summary": create_summary(
            endpoints
        ),
        "endpoints": endpoints,
    }

    json_path = (
        OUTPUT_DIR
        / "mvp01_api_probe.json"
    )

    md_path = (
        OUTPUT_DIR
        / "mvp01_api_probe.md"
    )

    json_path.write_text(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    md_path.write_text(
        markdown_report(
            data
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 72)
    print(
        "One UCH — MVP-01 API / Governance Probe"
    )
    print("=" * 72)
    print()

    print(
        "API endpoints:",
        data["summary"][
            "total_api_endpoints"
        ],
    )

    print()

    print(
        "Access classification:"
    )

    for key, value in (
        data["summary"][
            "access_classification"
        ].items()
    ):
        print(
            f"  {key}: {value}"
        )

    print()

    print(
        "Capability coverage:"
    )

    for key, value in (
        data["summary"][
            "capability_endpoint_counts"
        ].items()
    ):
        print(
            f"  {key}: {value}"
        )

    print()

    print(
        f"JSON report: {json_path}"
    )

    print(
        f"MD report:   {md_path}"
    )

    print()

    print(
        "No HTTP calls or database writes performed."
    )

    print()


if __name__ == "__main__":
    main()