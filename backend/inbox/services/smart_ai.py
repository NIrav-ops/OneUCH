import re


PRIORITY_KEYWORDS = [
    "urgent",
    "asap",
    "important",
    "immediately",
    "payment",
    "invoice",
    "overdue",
]

FINANCE_KEYWORDS = [
    "invoice",
    "payment",
    "amount due",
    "bank",
    "transaction",
]

MEETING_KEYWORDS = [
    "meeting",
    "schedule",
    "zoom",
    "google meet",
    "teams",
]


def analyze_email(subject: str, body: str):
    text = f"{subject} {body}".lower()

    priority_score = sum(1 for word in PRIORITY_KEYWORDS if word in text)

    tags = []

    if any(word in text for word in FINANCE_KEYWORDS):
        tags.append("finance")

    if any(word in text for word in MEETING_KEYWORDS):
        tags.append("meeting")

    if priority_score > 0:
        tags.append("priority")

    suggestion = generate_reply_suggestion(text, tags)

    return {
        "tags": tags,
        "suggested_reply": suggestion,
    }


def generate_reply_suggestion(text, tags):
    if "finance" in tags:
        return "Thank you for the invoice. We will review and process the payment shortly."

    if "meeting" in tags:
        return "Thank you for the meeting invite. Please confirm the proposed time."

    if "priority" in tags:
        return "We have received your urgent request and will respond as soon as possible."

    return "Thank you for your email. We will get back to you soon."
