import re


APPROVAL_PATTERNS = [
    {
        "pattern": (
            r"\b(?:please|kindly)\s+approve\b"
            r"|\bapproval\s+(?:is\s+)?required\b"
            r"|\brequires?\s+(?:your\s+)?approval\b"
            r"|\bneed\s+(?:your\s+)?approval\b"
        ),
        "title": "Approval Required",
        "priority": 90,
    },
    {
        "pattern": (
            r"\b(?:please|kindly)\s+sign[\s-]?off\b"
            r"|\bsign[\s-]?off\s+(?:is\s+)?required\b"
            r"|\bneed\s+(?:your\s+)?sign[\s-]?off\b"
        ),
        "title": "Sign Off Required",
        "priority": 85,
    },
    {
        "pattern": (
            r"\bcan\s+we\s+proceed\b"
            r"|\bok(?:ay)?\s+to\s+proceed\b"
            r"|\b(?:please|kindly)\s+confirm\s+"
            r"(?:that\s+)?we\s+can\s+proceed\b"
        ),
        "title": "Proceed Approval",
        "priority": 80,
    },
]


NON_APPROVAL_PATTERNS = [
    r"\balready\s+approved\b",
    r"\bapproval\s+(?:was|has\s+been)\s+completed\b",
    r"\bapproved\s+(?:yesterday|today|previously|already)\b",
    r"\bpermission\s+(?:was|has\s+been)\s+(?:already\s+)?granted\b",
    r"\bno\s+(?:further\s+)?approval\s+(?:is\s+)?required\b",
    r"\bapproval\s+(?:received|completed|granted)\b",
    r"\bthis\s+has\s+now\s+been\s+completed\b",
]


def _normalize_text(
    subject,
    body,
):
    return " ".join(
        f"{subject or ''} {body or ''}".split()
    ).lower()


def _extract_matching_evidence(
    subject,
    body,
    pattern,
):
    for value in (
        body or "",
        subject or "",
    ):
        sentences = re.split(
            r"(?<=[.!?])\s+|\r?\n+",
            value.strip(),
        )

        for sentence in sentences:
            sentence = (
                sentence.strip()
            )

            if not sentence:
                continue

            if re.search(
                pattern,
                sentence,
                flags=re.IGNORECASE,
            ):
                return sentence

    return ""


def extract_approvals(
    subject,
    body,
):
    text = _normalize_text(
        subject,
        body,
    )

    if any(
        re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )
        for pattern in NON_APPROVAL_PATTERNS
    ):
        return []

    for item in APPROVAL_PATTERNS:

        if re.search(
            item["pattern"],
            text,
            flags=re.IGNORECASE,
        ):
            return [
                {
                    "title": item["title"],
                    "description": (
                        subject
                        or (body or "")[:200]
                    ),
                    "priority": item[
                        "priority"
                    ],
                    "confidence_score": 85,
                    "due_date": None,
                    "evidence":
                        _extract_matching_evidence(
                            subject,
                            body,
                            item["pattern"],
                        ),
                }
            ]

    return []


def detect_approval_followup(
    subject,
    body,
):
    """
    Follow-up semantics are handled separately.

    Keep this compatibility function so the existing
    worker import does not break, but do not fabricate
    an approval deadline.
    """

    return None
