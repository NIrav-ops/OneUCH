import re
from datetime import timedelta
from django.utils import timezone


ACTION_PATTERNS = [
    {
        "pattern": r"approve",
        "title": "Approval Required",
        "priority": 90,
    },
    {
        "pattern": r"review",
        "title": "Review Required",
        "priority": 70,
    },
    {
        "pattern": r"quotation|quote",
        "title": "Send Quotation",
        "priority": 85,
    },
    {
        "pattern": r"payment|invoice",
        "title": "Payment Action",
        "priority": 95,
    },
    {
        "pattern": r"follow up|follow-up",
        "title": "Follow Up Required",
        "priority": 80,
    },
]

def extract_actions(subject, body):

    text = f"{subject} {body}".lower()

    actions = []

    for item in ACTION_PATTERNS:

        if re.search(item["pattern"], text):

            actions.append({
                "title": item["title"],
                "description": subject,
                "priority": item["priority"],
                "confidence_score": 80,
            })

    return actions

def detect_followup(subject, body):

    text = f"{subject} {body}".lower()

    followup_keywords = [
        "follow up",
        "follow-up",
        "waiting",
        "pending",
        "response",
        "reply",
    ]

    if any(word in text for word in followup_keywords):

        return {
            "followup_due_at":
                timezone.now() + timedelta(days=3)
        }

    return None