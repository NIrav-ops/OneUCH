from pathlib import Path


TEST_FILES = [
    "context/tests/test_ai_api.py",
    "context/tests/test_communication_api.py",
    "context/tests/test_customer360_api.py",
    "context/tests/test_executive_dashboard_api.py",
    "context/tests/test_opportunity_api.py",
    "context/tests/test_organization360_api.py",
    "context/tests/test_people360_api.py",
    "context/tests/test_risk_api.py",
    "context/tests/test_search_api.py",
    "context/tests/test_workflow_api.py",
]


def patch_file(path):
    text = path.read_text(
        encoding="utf-8-sig"
    )

    if "OrganizationUser.objects.create" in text:
        print(f"UNCHANGED - {path}")
        return

    if "from inbox.models import Organization" in text:
        text = text.replace(
            "from inbox.models import Organization",
            "from inbox.models import Organization, OrganizationUser",
            1,
        )
    else:
        raise RuntimeError(
            f"Could not find Organization import: {path}"
        )

    marker = (
        "self.organization = Organization.objects.create("
    )

    start = text.find(marker)

    if start == -1:
        raise RuntimeError(
            f"Organization creation block not found: {path}"
        )

    open_paren = text.find(
        "(",
        start,
    )

    depth = 0
    end = None

    for index in range(
        open_paren,
        len(text),
    ):
        char = text[index]

        if char == "(":
            depth += 1

        elif char == ")":
            depth -= 1

            if depth == 0:
                end = index + 1
                break

    if end is None:
        raise RuntimeError(
            f"Organization block incomplete: {path}"
        )

    membership = '''

        OrganizationUser.objects.create(
            user=self.user,
            organization=self.organization,
            role="member",
        )'''

    text = (
        text[:end]
        + membership
        + text[end:]
    )

    path.write_text(
        text,
        encoding="utf-8",
    )

    print(f"UPDATED - {path}")


for file_name in TEST_FILES:
    path = Path(file_name)

    if not path.exists():
        print(f"SKIP - {path}")
        continue

    try:
        patch_file(path)

    except Exception as exc:
        print(f"ERROR - {path}: {exc}")


print()
print("Context API membership patch complete.")
