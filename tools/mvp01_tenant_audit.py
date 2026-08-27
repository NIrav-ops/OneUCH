from pathlib import Path
import re
from collections import defaultdict


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"

TARGETS = [
    BACKEND / "knowledge",
    BACKEND / "workflow",
]

OUTPUT_DIR = ROOT / "artifacts" / "mvp01"
OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

OUTPUT_FILE = (
    OUTPUT_DIR
    / "mvp01_knowledge_workflow_tenant_audit.txt"
)


PATTERNS = {
    "RAW_GET": re.compile(
        r"\.objects\.get\s*\("
    ),
    "RAW_FILTER": re.compile(
        r"\.objects\.filter\s*\("
    ),
    "RAW_EXCLUDE": re.compile(
        r"\.objects\.exclude\s*\("
    ),
    "GET_OBJECT_OR_404": re.compile(
        r"get_object_or_404\s*\("
    ),
    "PK_LOOKUP": re.compile(
        r"\b(pk|id|_id)\s*="
    ),
    "ORGANIZATION_SCOPE": re.compile(
        r"\borganization\s*="
    ),
    "ORGANIZATION_ID": re.compile(
        r"\borganization_id\b"
    ),
    "REQUEST_USER": re.compile(
        r"\brequest\.user\b"
    ),
    "USER_SCOPE": re.compile(
        r"\buser\s*="
    ),
    "BUSINESS_OBJECT": re.compile(
        r"\bbusiness_object(_id)?\b"
    ),
    "CONVERSATION": re.compile(
        r"\bconversation(_id)?\b"
    ),
    "MESSAGE": re.compile(
        r"\bmessage(_id)?\b"
    ),
    "TASK": re.compile(
        r"@(shared_task|task)|\bdef\s+\w*task\w*\s*\(",
        re.IGNORECASE,
    ),
    "SERVICE_CLASS": re.compile(
        r"\bclass\s+\w*(Service|Repository|Resolver|Executor|Engine)\b"
    ),
    "EXECUTE_METHOD": re.compile(
        r"\bdef\s+(execute|run|process|resolve|build|create|get|find|search)\s*\("
    ),
}


def iter_python_files():
    for target in TARGETS:

        if not target.exists():
            continue

        for path in target.rglob("*.py"):

            if "__pycache__" in path.parts:
                continue

            if "migrations" in path.parts:
                continue

            yield path


def relative(path):
    return path.relative_to(ROOT)


def classify_file(path, text):
    categories = []

    lower_parts = [
        part.lower()
        for part in path.parts
    ]

    if "tests" in lower_parts:
        categories.append("TEST")

    if path.name == "models.py":
        categories.append("MODEL")

    if "repositories" in lower_parts or "repository" in path.name.lower():
        categories.append("REPOSITORY")

    if "services" in lower_parts or "service" in path.name.lower():
        categories.append("SERVICE")

    if "tasks.py" == path.name or "task" in path.name.lower():
        categories.append("TASK")

    if "views.py" == path.name or "view" in path.name.lower():
        categories.append("API")

    if (
        "executor" in path.name.lower()
        or "runtime" in lower_parts
        or "engine" in path.name.lower()
    ):
        categories.append("RUNTIME")

    return categories or ["OTHER"]


def main():

    files = list(iter_python_files())

    results = defaultdict(list)

    risky_files = set()

    explicit_org_files = set()

    repository_files = set()

    task_files = set()

    runtime_files = set()

    for path in files:

        try:
            text = path.read_text(
                encoding="utf-8-sig"
            )
        except UnicodeDecodeError:
            text = path.read_text(
                encoding="utf-8",
                errors="replace",
            )

        categories = classify_file(
            path,
            text,
        )

        if "REPOSITORY" in categories:
            repository_files.add(path)

        if "TASK" in categories:
            task_files.add(path)

        if "RUNTIME" in categories:
            runtime_files.add(path)

        lines = text.splitlines()

        for line_no, line in enumerate(
            lines,
            start=1,
        ):

            stripped = line.strip()

            if not stripped:
                continue

            if stripped.startswith("#"):
                continue

            matched = []

            for name, pattern in PATTERNS.items():

                if pattern.search(line):
                    matched.append(name)

            if not matched:
                continue

            if any(
                item in matched
                for item in [
                    "RAW_GET",
                    "RAW_FILTER",
                    "RAW_EXCLUDE",
                    "GET_OBJECT_OR_404",
                    "PK_LOOKUP",
                ]
            ):
                risky_files.add(path)

            if (
                "ORGANIZATION_SCOPE" in matched
                or "ORGANIZATION_ID" in matched
            ):
                explicit_org_files.add(path)

            results[path].append(
                (
                    line_no,
                    matched,
                    stripped,
                )
            )

    output = []

    output.append(
        "=" * 78
    )
    output.append(
        "MVP-01 KNOWLEDGE + WORKFLOW TENANT ISOLATION AUDIT"
    )
    output.append(
        "=" * 78
    )
    output.append("")
    output.append(
        f"Repository root: {ROOT}"
    )
    output.append(
        f"Python files scanned: {len(files)}"
    )
    output.append("")

    output.append(
        "AUDIT GOAL"
    )
    output.append(
        "-" * 78
    )
    output.append(
        "Find confirmed tenant-boundary risks only."
    )
    output.append(
        "No feature/refactor recommendations are implied by this report."
    )
    output.append("")

    output.append(
        "SUMMARY"
    )
    output.append(
        "-" * 78
    )
    output.append(
        f"Files containing ORM/object lookup patterns: {len(risky_files)}"
    )
    output.append(
        f"Files containing explicit organization scope/id: {len(explicit_org_files)}"
    )
    output.append(
        f"Repository files: {len(repository_files)}"
    )
    output.append(
        f"Task files: {len(task_files)}"
    )
    output.append(
        f"Runtime/executor files: {len(runtime_files)}"
    )
    output.append("")

    output.append(
        "HIGH-PRIORITY REVIEW CANDIDATES"
    )
    output.append(
        "-" * 78
    )
    output.append(
        "These files contain lookup patterns but no obvious organization "
        "scope token in the same file. They REQUIRE manual review; they are "
        "not automatically vulnerabilities."
    )
    output.append("")

    candidates = sorted(
        risky_files - explicit_org_files,
        key=lambda p: str(p),
    )

    if candidates:

        for path in candidates:
            output.append(
                f"REVIEW  {relative(path)}"
            )

    else:
        output.append(
            "None detected by static scan."
        )

    output.append("")

    output.append(
        "REPOSITORY FILES"
    )
    output.append(
        "-" * 78
    )

    for path in sorted(
        repository_files,
        key=lambda p: str(p),
    ):
        org = (
            "ORG-SCOPE TOKEN FOUND"
            if path in explicit_org_files
            else "REVIEW ORG SCOPE"
        )

        output.append(
            f"{org:24} {relative(path)}"
        )

    output.append("")

    output.append(
        "TASK FILES"
    )
    output.append(
        "-" * 78
    )

    for path in sorted(
        task_files,
        key=lambda p: str(p),
    ):
        org = (
            "ORG-SCOPE TOKEN FOUND"
            if path in explicit_org_files
            else "REVIEW ORG SCOPE"
        )

        output.append(
            f"{org:24} {relative(path)}"
        )

    output.append("")

    output.append(
        "WORKFLOW RUNTIME / EXECUTOR FILES"
    )
    output.append(
        "-" * 78
    )

    for path in sorted(
        runtime_files,
        key=lambda p: str(p),
    ):
        org = (
            "ORG-SCOPE TOKEN FOUND"
            if path in explicit_org_files
            else "REVIEW ORG SCOPE"
        )

        output.append(
            f"{org:24} {relative(path)}"
        )

    output.append("")

    output.append(
        "DETAILED MATCHES"
    )
    output.append(
        "=" * 78
    )

    for path in sorted(
        results.keys(),
        key=lambda p: str(p),
    ):

        categories = ", ".join(
            classify_file(
                path,
                "",
            )
        )

        output.append("")
        output.append(
            f"FILE: {relative(path)}"
        )
        output.append(
            f"TYPE: {categories}"
        )
        output.append(
            "-" * 78
        )

        for line_no, matched, line in results[path]:

            tags = ",".join(matched)

            output.append(
                f"{line_no:5} [{tags}]"
            )
            output.append(
                f"      {line}"
            )

    OUTPUT_FILE.write_text(
        "\n".join(output),
        encoding="utf-8",
    )

    print(
        "MVP-01 Knowledge + Workflow tenant audit complete."
    )
    print(
        f"Scanned: {len(files)} Python files"
    )
    print(
        f"Lookup candidate files: {len(risky_files)}"
    )
    print(
        f"Explicit org-scope files: {len(explicit_org_files)}"
    )
    print(
        f"Report: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
