import re
from datetime import timedelta
from django.utils import timezone


APPROVAL_PATTERNS = [
    {
        "pattern": r"\bapprove\b",
        "title": "Approval Required",
        "priority": 90,
    },
    {
        "pattern": r"\bapproval\b",
        "title": "Approval Required",
        "priority": 90,
    },
    {
        "pattern": r"sign off|sign-off",
        "title": "Sign Off Required",
        "priority": 85,
    },
    {
        "pattern": r"review and confirm|confirm",
        "title": "Confirmation Required",
        "priority": 80,
    },
    {
        "pattern": r"ok to proceed|okay to proceed|can we proceed",
        "title": "Proceed Approval",
        "priority": 80,
    },
    {
        "pattern": r"permission|required approval|need your approval",
        "title": "Approval Required",
        "priority": 90,
    },
    {
        "pattern": r"please review|kindly review",
        "title": "Review Before Approval",
        "priority": 75,
    },
]


def extract_approvals(subject, body):
    text = f"{subject} {body}".lower()
    approvals = []

    for item in APPROVAL_PATTERNS:
        if re.search(item["pattern"], text):
            approvals.append({
                "title": item["title"],
                "description": subject or body[:200],
                "priority": item["priority"],
                "confidence_score": 85,
                "due_date": timezone.now() + timedelta(days=2),
            })

    return approvals


def detect_approval_followup(subject, body):
    text = f"{subject} {body}".lower()

    followup_keywords = [
        "approve",
        "approval",
        "sign off",
        "confirm",
        "proceed",
        "permission",
        "review",
    ]

    if any(word in text for word in followup_keywords):
        return timezone.now() + timedelta(days=2)

    return None