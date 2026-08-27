import re
from datetime import timedelta, datetime

from django.utils import timezone


ACTION_PATTERNS = [
    {
        "trigger": r"\bapprove|approval\b",
        "intent": (
            r"\b(?:please|kindly)\s+approve\b"
            r"|\bapproval\s+(?:is\s+)?required\b"
            r"|\brequires?\s+(?:your\s+)?approval\b"
        ),
        "title": "Approval Required",
        "priority": 90,
    },
    {
        "trigger": r"\breview\b",
        "intent": (
            r"\b(?:please|kindly)\s+review\b"
            r"|\breview\s+(?:is\s+)?required\b"
            r"|\brequires?\s+(?:your\s+)?review\b"
        ),
        "title": "Review Required",
        "priority": 70,
    },
    {
        "trigger": r"\b(?:quotation|quote)\b",
        "intent": (
            r"\b(?:please|kindly)\s+"
            r"(?:send|share|provide|prepare|submit)"
            r"(?:\s+and\s+(?:send|share|provide|submit))?\s+"
            r"(?:the\s+)?(?:revised\s+)?"
            r"(?:quotation|quote)\b"
            r"|\b(?:quotation|quote)\s+"
            r"(?:is\s+)?required\b"
            r"|\brequest(?:ing|ed)?\s+"
            r"(?:a\s+)?(?:quotation|quote)\b"
        ),
        "title": "Send Quotation",
        "priority": 85,
    },
    {
        "trigger": r"\b(?:payment|invoice)\b",
        "intent": (
            r"\b(?:please|kindly)\s+"
            r"(?:make|process|release|arrange|confirm)\s+"
            r"(?:the\s+)?(?:attached\s+)?"
            r"(?:payment|invoice)\b"
            r"|\b(?:payment|invoice)\s+"
            r"(?:is\s+)?(?:due|pending|overdue)\b"
            r"|\b(?:payment|invoice)\s+"
            r"(?:processing|approval)\s+required\b"
        ),
        "title": "Payment Action",
        "priority": 95,
    },
    {
        "trigger": r"\bfollow[ -]?up\b",
        "intent": (
            r"\b(?:please|kindly)\s+follow[ -]?up\b"
            r"|\bfollow[ -]?up\s+"
            r"(?:is\s+)?required\b"
            r"|\bneed(?:s)?\s+to\s+follow[ -]?up\b"
        ),
        "title": "Follow Up Required",
        "priority": 80,
    },
]


NON_ACTION_PATTERNS = [
    r"\bno\s+(?:further\s+)?action\s+(?:is\s+)?required\b",
    r"\bfor\s+your\s+records\b",
    r"\bpayment\s+(?:has\s+been\s+)?received\b",
    r"\bpayment\s+received\s+successfully\b",
]


def _extract_due_date(text, reference_time=None):

    reference_time = reference_time or timezone.now()

    # ISO date: YYYY-MM-DD
    iso_match = re.search(
        r"\bby\s+(\d{4}-\d{2}-\d{2})\b",
        text,
    )

    if iso_match:
        parsed = datetime.strptime(
            iso_match.group(1),
            "%Y-%m-%d",
        )

        due_date = timezone.make_aware(
            parsed,
            timezone.get_current_timezone(),
        )

        if due_date >= reference_time:
            return due_date

    # Relative deadline: tomorrow
    if re.search(
        r"\bby\s+tomorrow\b",
        text,
    ):
        return reference_time + timedelta(days=1)

    # Named weekday deadline
    weekdays = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }

    weekday_match = re.search(
        r"\bby\s+"
        r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
        r"\b",
        text,
    )

    if weekday_match:
        target_weekday = weekdays[
            weekday_match.group(1)
        ]

        current_weekday = reference_time.weekday()

        days_ahead = (
            target_weekday - current_weekday
        ) % 7

        if days_ahead == 0:
            days_ahead = 7

        return reference_time + timedelta(
            days=days_ahead
        )

    return None

def extract_actions(
    subject,
    body,
    reference_time=None,
):

    text = f"{subject} {body}".lower()

    if any(
        re.search(pattern, text)
        for pattern in NON_ACTION_PATTERNS
    ):
        return []

    actions = []

    due_date = _extract_due_date(
        text,
        reference_time=reference_time,
    )

    for item in ACTION_PATTERNS:

        trigger_found = re.search(
            item["trigger"],
            text,
        )

        intent_found = re.search(
            item["intent"],
            text,
        )

        if trigger_found and intent_found:

            actions.append({
                "title": item["title"],
                "description": subject,
                "priority": item["priority"],
                "confidence_score": 80,
                "due_date": due_date,
            })

    return actions


def detect_followup(
    subject,
    body,
    *,
    reference_time=None,
):
    """
    Detect an explicit follow-up obligation.

    Precision is intentionally preferred over recall.

    Generic words such as waiting, pending, response,
    and reply are NOT sufficient to create a follow-up.

    A due date is returned only when the source text
    explicitly contains a supported relative date.
    """

    import re
    from datetime import timedelta

    from django.utils import timezone

    subject = subject or ""
    body = body or ""

    text = (
        f"{subject} {body}"
        .strip()
        .lower()
    )

    if not text:
        return None

    # --------------------------------------------------
    # Explicit negative / historical contexts.
    # These must not generate a new follow-up.
    # --------------------------------------------------

    negative_patterns = [
        r"\bthanks?\s+for\s+the\s+follow[\s-]?up\b",
        r"\bthank\s+you\s+for\s+the\s+follow[\s-]?up\b",
        r"\bfollowed\s+up\b",
        r"\balready\s+followed\s+up\b",
        r"\bissue\s+is\s+(?:now\s+)?resolved\b",
        r"\bhas\s+been\s+resolved\b",
        r"\bwas\s+resolved\b",
        r"\bfollow[\s-]?up\s+webinar\b",
    ]

    if any(
        re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )
        for pattern in negative_patterns
    ):
        return None

    # --------------------------------------------------
    # A follow-up must contain an explicit instruction
    # or explicit reconnect intent.
    #
    # Do NOT trigger on:
    # waiting / pending / response / reply
    # --------------------------------------------------

    explicit_patterns = [
        r"\bplease\s+follow[\s-]?up\b",
        r"\bkindly\s+follow[\s-]?up\b",
        r"\bfollow[\s-]?up\s+with\b",
        r"\blet['?]?s\s+reconnect\b",
        r"\bplease\s+reconnect\b",
        r"\bkindly\s+reconnect\b",
    ]

    if not any(
        re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )
        for pattern in explicit_patterns
    ):
        return None

    if reference_time is None:
        reference_time = (
            timezone.now()
        )

    # Keep timezone information from the supplied
    # reference timestamp.
    base_date = (
        reference_time
        .replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
    )

    due_at = None

    # --------------------------------------------------
    # Explicit relative dates.
    # --------------------------------------------------

    if re.search(
        r"\btomorrow\b",
        text,
        flags=re.IGNORECASE,
    ):
        due_at = (
            base_date
            + timedelta(
                days=1
            )
        )

    elif re.search(
        r"\btoday\b",
        text,
        flags=re.IGNORECASE,
    ):
        due_at = base_date

    else:
        weekdays = {
            "monday": 0,
            "tuesday": 1,
            "wednesday": 2,
            "thursday": 3,
            "friday": 4,
            "saturday": 5,
            "sunday": 6,
        }

        for (
            weekday_name,
            weekday_number,
        ) in weekdays.items():

            next_match = re.search(
                rf"\bnext\s+{weekday_name}\b",
                text,
                flags=re.IGNORECASE,
            )

            by_match = re.search(
                rf"\bby\s+{weekday_name}\b",
                text,
                flags=re.IGNORECASE,
            )

            plain_match = re.search(
                rf"\b{weekday_name}\b",
                text,
                flags=re.IGNORECASE,
            )

            if next_match:
                days_ahead = (
                    weekday_number
                    - base_date.weekday()
                ) % 7

                if days_ahead == 0:
                    days_ahead = 7

                due_at = (
                    base_date
                    + timedelta(
                        days=days_ahead
                    )
                )

                break

            if (
                by_match
                or plain_match
            ):
                days_ahead = (
                    weekday_number
                    - base_date.weekday()
                ) % 7

                due_at = (
                    base_date
                    + timedelta(
                        days=days_ahead
                    )
                )

                break

    return {
        "followup_due_at": due_at,
    }

