from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
FRONTEND_SRC = FRONTEND / "src"
OUTPUT_DIR = ROOT / "artifacts" / "mvp01"

EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".pytest_cache",
    ".mypy_cache",
}

SECRET_FILE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    "credentials.json",
    "client_secret.json",
    "service-account.json",
}

SENSITIVE_PATTERNS = {
    "hardcoded_django_secret": re.compile(
        r"""SECRET_KEY\s*=\s*["'][^"']+["']""",
        re.IGNORECASE,
    ),
    "debug_true": re.compile(
        r"\bDEBUG\s*=\s*True\b",
        re.IGNORECASE,
    ),
    "cors_allow_all": re.compile(
        r"\bCORS_ALLOW_ALL_ORIGINS\s*=\s*True\b",
        re.IGNORECASE,
    ),
    "allow_any": re.compile(
        r"\bAllowAny\b",
    ),
}

URL_PATTERN = re.compile(
    r"""path\(\s*["']([^"']*)["']""",
    re.MULTILINE,
)

INCLUDE_PATTERN = re.compile(
    r"""include\(\s*["']([^"']+)["']""",
    re.MULTILINE,
)

FRONTEND_ROUTE_PATTERNS = [
    re.compile(
        r"""<Route[^>]*\spath\s*=\s*["']([^"']+)["']""",
        re.IGNORECASE,
    ),
    re.compile(
        r"""path\s*:\s*["']([^"']+)["']""",
        re.IGNORECASE,
    ),
]

API_REFERENCE_PATTERN = re.compile(
    r"""["'`](/?api/[A-Za-z0-9_./?={}&:-]+)["'`]"""
)


def should_skip(path: Path) -> bool:
    return any(part in EXCLUDED_PARTS for part in path.parts)


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def run_git(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if result.returncode != 0:
            return ""
        return result.stdout.strip()
    except Exception:
        return ""


def read_text(path: Path) -> str:
    try:
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        return ""


def collect_files(base: Path, suffixes: set[str]) -> list[Path]:
    if not base.exists():
        return []

    results = []

    for path in base.rglob("*"):
        if not path.is_file():
            continue

        if should_skip(path):
            continue

        if path.suffix.lower() in suffixes:
            results.append(path)

    return sorted(results)


def collect_git_state() -> dict:
    status = run_git("status", "--porcelain")

    return {
        "branch": run_git(
            "rev-parse",
            "--abbrev-ref",
            "HEAD",
        ),
        "head": run_git(
            "rev-parse",
            "HEAD",
        ),
        "head_short": run_git(
            "rev-parse",
            "--short",
            "HEAD",
        ),
        "latest_commit": run_git(
            "log",
            "-1",
            "--pretty=%h %ad %s",
            "--date=iso",
        ),
        "origin_main": run_git(
            "rev-parse",
            "origin/main",
        ),
        "working_tree_clean": not bool(status),
        "working_tree_changes": (
            status.splitlines()
            if status
            else []
        ),
    }


def collect_backend_apps() -> list[dict]:
    apps = []

    if not BACKEND.exists():
        return apps

    for directory in sorted(BACKEND.iterdir()):
        if not directory.is_dir():
            continue

        if should_skip(directory):
            continue

        markers = {
            "apps_py": (directory / "apps.py").exists(),
            "models_py": (directory / "models.py").exists(),
            "urls_py": (directory / "urls.py").exists(),
            "views_py": (directory / "views.py").exists(),
            "tests_py": (directory / "tests.py").exists(),
            "services_dir": (directory / "services").exists(),
            "migrations_dir": (directory / "migrations").exists(),
        }

        if any(markers.values()):
            apps.append(
                {
                    "name": directory.name,
                    **markers,
                }
            )

    return apps


def collect_urls() -> list[dict]:
    results = []

    for path in collect_files(BACKEND, {".py"}):
        if path.name != "urls.py":
            continue

        text = read_text(path)

        routes = URL_PATTERN.findall(text)
        includes = INCLUDE_PATTERN.findall(text)

        results.append(
            {
                "file": relative(path),
                "routes": sorted(set(routes)),
                "includes": sorted(set(includes)),
            }
        )

    return results


def collect_backend_structure() -> dict:
    python_files = collect_files(BACKEND, {".py"})

    models = []
    serializers = []
    services = []
    tasks = []
    tests = []
    views = []

    for path in python_files:
        rel = relative(path)
        parts = set(path.parts)

        if path.name == "models.py" or "models" in parts:
            models.append(rel)

        if "serializer" in path.name.lower():
            serializers.append(rel)

        if "services" in parts:
            services.append(rel)

        if path.name == "tasks.py":
            tasks.append(rel)

        if (
            path.name.startswith("test_")
            or path.name == "tests.py"
            or "tests" in parts
        ):
            tests.append(rel)

        if (
            path.name == "views.py"
            or "views" in parts
        ):
            views.append(rel)

    return {
        "python_file_count": len(python_files),
        "model_files": sorted(set(models)),
        "serializer_files": sorted(set(serializers)),
        "service_files": sorted(set(services)),
        "task_files": sorted(set(tasks)),
        "view_files": sorted(set(views)),
        "test_files": sorted(set(tests)),
        "test_file_count": len(set(tests)),
    }


def collect_frontend() -> dict:
    source_files = collect_files(
        FRONTEND_SRC,
        {".js", ".jsx", ".ts", ".tsx"},
    )

    pages = []
    services = []
    components = []
    routes = set()
    api_references = set()

    for path in source_files:
        rel = relative(path)
        text = read_text(path)

        if "/pages/" in f"/{rel}":
            pages.append(rel)

        if "/services/" in f"/{rel}":
            services.append(rel)

        if "/components/" in f"/{rel}":
            components.append(rel)

        for pattern in FRONTEND_ROUTE_PATTERNS:
            routes.update(pattern.findall(text))

        api_references.update(
            API_REFERENCE_PATTERN.findall(text)
        )

    return {
        "source_file_count": len(source_files),
        "pages": sorted(set(pages)),
        "services": sorted(set(services)),
        "components": sorted(set(components)),
        "routes": sorted(routes),
        "api_references": sorted(api_references),
    }


def collect_security_signals() -> dict:
    tracked = set(
        run_git("ls-files").splitlines()
    )

    tracked_secret_files = sorted(
        item
        for item in tracked
        if Path(item).name.lower()
        in SECRET_FILE_NAMES
    )

    findings = []

    candidates = collect_files(
        BACKEND,
        {".py"},
    )

    for path in candidates:
        text = read_text(path)

        for finding_name, pattern in SENSITIVE_PATTERNS.items():
            matches = pattern.findall(text)

            if matches:
                findings.append(
                    {
                        "type": finding_name,
                        "file": relative(path),
                        "match_count": len(matches),
                    }
                )

    env_names = set()

    env_pattern = re.compile(
        r"""(?:os\.getenv|os\.environ\.get)\(\s*["']([^"']+)["']"""
    )

    for path in candidates:
        text = read_text(path)
        env_names.update(env_pattern.findall(text))

    return {
        "tracked_secret_like_files": tracked_secret_files,
        "environment_variable_names": sorted(env_names),
        "review_signals": findings,
        "note": (
            "Review signals are audit hints only. "
            "AllowAny and DEBUG may be intentional depending on endpoint/environment."
        ),
    }


def classify_surface(
    name: str,
    backend_apps: set[str],
    frontend_files: list[str],
) -> dict:
    """
    Conservative structural classification only.

    This does NOT claim runtime functionality.
    Runtime status must be verified separately.
    """

    aliases = {
        "Authentication": {"accounts", "authentication"},
        "Inbox": {"inbox", "conversations"},
        "Gmail": {"googleapis"},
        "Microsoft": {"microsoftapis"},
        "Email Accounts": {"email_accounts"},
        "Actions": {"actions"},
        "Approvals": {"approvals"},
        "Knowledge": {"knowledge"},
        "Timeline": {"timeline"},
        "Notifications": {"notifications"},
        "Search": {"search"},
        "Workflow": {"workflow"},
        "Audit": {"audit_logs"},
        "Context": {"context"},
        "Platform": {"platform_core"},
    }

    expected_apps = aliases.get(name, set())

    backend_present = bool(
        expected_apps & backend_apps
    )

    name_lower = name.lower().replace(" ", "")

    ui_present = any(
        name_lower in Path(item).stem.lower().replace(
            "_",
            "",
        ).replace("-", "")
        for item in frontend_files
    )

    if backend_present and ui_present:
        structural_state = "PRESENT_BACKEND_AND_UI"
    elif backend_present:
        structural_state = "BACKEND_PRESENT_UI_UNCONFIRMED"
    elif ui_present:
        structural_state = "UI_PRESENT_BACKEND_UNCONFIRMED"
    else:
        structural_state = "NOT_CONFIRMED"

    return {
        "capability": name,
        "structural_state": structural_state,
        "runtime_state": "REQUIRES_VERIFICATION",
        "mvp_classification": "REQUIRES_AUDIT",
    }


def build_report(data: dict) -> str:
    git = data["git"]
    backend_apps = data["backend_apps"]
    backend = data["backend"]
    frontend = data["frontend"]
    security = data["security"]

    lines = [
        "# One UCH — MVP-01 Controlled Gap Audit",
        "",
        f"Generated: {data['generated_at']}",
        "",
        "## 1. Repository Baseline",
        "",
        f"- Branch: `{git['branch'] or 'unknown'}`",
        f"- HEAD: `{git['head'] or 'unknown'}`",
        f"- Latest commit: `{git['latest_commit'] or 'unknown'}`",
        f"- Working tree clean: `{git['working_tree_clean']}`",
        f"- Local changes: `{len(git['working_tree_changes'])}`",
        "",
        "## 2. Backend Inventory",
        "",
        f"- Django-style apps detected: `{len(backend_apps)}`",
        f"- Python files: `{backend['python_file_count']}`",
        f"- View files: `{len(backend['view_files'])}`",
        f"- Service files: `{len(backend['service_files'])}`",
        f"- Task files: `{len(backend['task_files'])}`",
        f"- Test files: `{backend['test_file_count']}`",
        "",
        "### Applications",
        "",
    ]

    for app in backend_apps:
        lines.append(
            f"- `{app['name']}` "
            f"(models={app['models_py']}, "
            f"urls={app['urls_py']}, "
            f"services={app['services_dir']}, "
            f"tests={app['tests_py']})"
        )

    lines.extend(
        [
            "",
            "## 3. API URL Inventory",
            "",
        ]
    )

    for item in data["urls"]:
        lines.append(f"### `{item['file']}`")
        lines.append("")

        if item["routes"]:
            for route in item["routes"]:
                lines.append(f"- `{route}`")
        else:
            lines.append("- No direct `path()` routes detected.")

        if item["includes"]:
            lines.append("")
            lines.append("Includes:")

            for include in item["includes"]:
                lines.append(f"- `{include}`")

        lines.append("")

    lines.extend(
        [
            "## 4. Frontend Inventory",
            "",
            f"- Source files: `{frontend['source_file_count']}`",
            f"- Pages: `{len(frontend['pages'])}`",
            f"- Components: `{len(frontend['components'])}`",
            f"- Services: `{len(frontend['services'])}`",
            f"- Routes detected: `{len(frontend['routes'])}`",
            f"- API references detected: `{len(frontend['api_references'])}`",
            "",
            "### Pages",
            "",
        ]
    )

    for item in frontend["pages"]:
        lines.append(f"- `{item}`")

    lines.extend(
        [
            "",
            "### Frontend API References",
            "",
        ]
    )

    for item in frontend["api_references"]:
        lines.append(f"- `{item}`")

    lines.extend(
        [
            "",
            "## 5. MVP Structural Matrix",
            "",
            "| Capability | Structural Evidence | Runtime | MVP Classification |",
            "|---|---|---|---|",
        ]
    )

    for item in data["mvp_surface"]:
        lines.append(
            f"| {item['capability']} "
            f"| {item['structural_state']} "
            f"| {item['runtime_state']} "
            f"| {item['mvp_classification']} |"
        )

    lines.extend(
        [
            "",
            "## 6. Security / Compliance Review Signals",
            "",
            f"- Tracked secret-like files: `{len(security['tracked_secret_like_files'])}`",
            f"- Environment variables referenced: `{len(security['environment_variable_names'])}`",
            f"- Review signals: `{len(security['review_signals'])}`",
            "",
        ]
    )

    for finding in security["review_signals"]:
        lines.append(
            f"- `{finding['type']}` → "
            f"`{finding['file']}` "
            f"({finding['match_count']} match(es))"
        )

    lines.extend(
        [
            "",
            "## 7. MVP-01 Classification Rule",
            "",
            "This report intentionally does **not** mark features as working "
            "from file presence alone.",
            "",
            "Final MVP-01 classification requires:",
            "",
            "1. Repository evidence",
            "2. API evidence",
            "3. UI evidence",
            "4. Runtime/test evidence",
            "5. Security / organization-boundary review",
            "",
            "Only after those checks should a capability become:",
            "",
            "- ALREADY WORKING",
            "- PARTIALLY WORKING",
            "- MISSING",
            "- MVP REQUIRED",
            "- DEFER",
            "",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    backend_apps = collect_backend_apps()

    backend_app_names = {
        item["name"]
        for item in backend_apps
    }

    frontend = collect_frontend()

    capabilities = [
        "Authentication",
        "Email Accounts",
        "Inbox",
        "Gmail",
        "Microsoft",
        "Actions",
        "Approvals",
        "Knowledge",
        "Timeline",
        "Notifications",
        "Search",
        "Workflow",
        "Audit",
        "Context",
        "Platform",
    ]

    data = {
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "repository_root": str(ROOT),
        "git": collect_git_state(),
        "backend_apps": backend_apps,
        "backend": collect_backend_structure(),
        "urls": collect_urls(),
        "frontend": frontend,
        "security": collect_security_signals(),
        "mvp_surface": [
            classify_surface(
                capability,
                backend_app_names,
                frontend["pages"]
                + frontend["services"]
                + frontend["components"],
            )
            for capability in capabilities
        ],
    }

    json_path = OUTPUT_DIR / "mvp01_inventory.json"
    md_path = OUTPUT_DIR / "mvp01_gap_audit.md"

    json_path.write_text(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    md_path.write_text(
        build_report(data),
        encoding="utf-8",
    )

    print()
    print("=" * 70)
    print("One UCH — MVP-01 Controlled Repository/API/UI Gap Audit")
    print("=" * 70)
    print()
    print(f"Repository : {ROOT}")
    print(
        f"HEAD       : "
        f"{data['git']['head_short'] or 'unknown'}"
    )
    print(
        f"Clean tree : "
        f"{data['git']['working_tree_clean']}"
    )
    print(
        f"Backend apps : {len(backend_apps)}"
    )
    print(
        f"Backend tests: "
        f"{data['backend']['test_file_count']}"
    )
    print(
        f"Frontend pages: "
        f"{len(frontend['pages'])}"
    )
    print()
    print(f"JSON report : {json_path}")
    print(f"MD report   : {md_path}")
    print()
    print(
        "No database writes, migrations, API calls, "
        "or production mutations were performed."
    )
    print()


if __name__ == "__main__":
    main()