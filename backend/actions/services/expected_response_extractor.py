import re
from datetime import timedelta

from django.utils import timezone


WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def _midnight(reference_time):
    return reference_time.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )


def _next_weekday(
    reference_time,
    weekday,
    *,
    force_next=False,
):
    base = _midnight(reference_time)

    days_ahead = (
        weekday - base.weekday()
    ) % 7

    if force_next and days_ahead == 0:
        days_ahead = 7

    return base + timedelta(
        days=days_ahead
    )


def _extract_due_at(
    text,
    *,
    reference_time,
):
    normalized = text.lower()

    base = _midnight(
        reference_time
    )

    if re.search(
        r"\btomorrow\b",
        normalized,
    ):
        return base + timedelta(days=1)

    if re.search(
        r"\btoday\b",
        normalized,
    ):
        return base

    for name, weekday in WEEKDAYS.items():
        if re.search(
            rf"\bnext\s+{name}\b",
            normalized,
        ):
            return _next_weekday(
                reference_time,
                weekday,
                force_next=True,
            )

    for name, weekday in WEEKDAYS.items():
        if re.search(
            rf"\b(?:by\s+)?{name}\b",
            normalized,
        ):
            return _next_weekday(
                reference_time,
                weekday,
            )

    return None


def _extract_email(text):
    match = re.search(
        (
            r"\b[A-Z0-9._%+-]+"
            r"@[A-Z0-9.-]+"
            r"\.[A-Z]{2,}\b"
        ),
        text,
        flags=re.IGNORECASE,
    )

    if match:
        return match.group(0)

    return None


def _extract_evidence(
    subject,
    body,
    patterns,
):
    candidates = []

    for value in (
        body or "",
        subject or "",
    ):
        for sentence in re.split(
            r"(?<=[.!?])\s+",
            value.strip(),
        ):
            sentence = (
                sentence.strip()
            )

            if not sentence:
                continue

            if any(
                re.search(
                    pattern,
                    sentence,
                    flags=re.IGNORECASE,
                )
                for pattern in patterns
            ):
                candidates.append(
                    sentence
                )

    if candidates:
        return candidates[0]

    return (body or subject or "").strip()


def detect_expected_response(
    subject,
    body,
    *,
    reference_time=None,
):
    """
    Detect a narrow, deterministic expected-response
    obligation.

    This is intentionally separate from explicit
    FollowUpItem detection.

    Accepted examples:
    - We will send the revised quotation by Friday.
    - Vendor will confirm tomorrow.
    - Customer will get back to us next Monday.
    - Please let me know once approved.

    Generic waiting/pending language is intentionally
    insufficient.
    """

    subject = subject or ""
    body = body or ""

    text = " ".join(
        part.strip()
        for part in (
            subject,
            body,
        )
        if part and part.strip()
    )

    if not text:
        return None

    normalized = text.lower()

    # --------------------------------------------------
    # Explicit exclusions
    #
    # These belong to other intelligence domains or
    # describe historical/completed state.
    # --------------------------------------------------

    exclusion_patterns = [
        r"\bfollow[\s-]?up\b",
        r"\breconnect\b",
        r"\bwe\s+are\s+waiting\b",
        r"\bwe['?]?re\s+waiting\b",
        r"\bstill\s+waiting\b",
        r"\bpending\b",
        r"\bthanks?\s+for\s+(?:the\s+)?response\b",
        r"\bthank\s+you\s+for\s+(?:the\s+)?response\b",
        r"\bresponse\s+received\b",
        r"\breceived\s+(?:the\s+)?response\b",
        r"\bwe\s+sent\b",
        r"\bhas\s+sent\b",
        r"\bhave\s+sent\b",
        r"\bsent\s+.*\byesterday\b",
    ]

    if any(
        re.search(
            pattern,
            normalized,
            flags=re.IGNORECASE,
        )
        for pattern in exclusion_patterns
    ):
        return None

    # --------------------------------------------------
    # Precision-first commitment patterns.
    #
    # These require an explicit future response,
    # confirmation, send/share/update commitment, or
    # explicit request to be informed later.
    # --------------------------------------------------

    commitment_patterns = [
        (
            r"\b(?:we|i|vendor|customer|client|supplier|"
            r"partner|team|they|he|she)\s+"
            r"(?:will|shall)\s+"
            r"(?:send|share|provide|confirm|update|reply|"
            r"respond|revert)\b"
        ),
        (
            r"\b(?:vendor|customer|client|supplier|"
            r"partner|they|he|she)\s+"
            r"(?:will|shall)\s+"
            r"get\s+back\b"
        ),
        (
            r"\bplease\s+let\s+me\s+know\s+"
            r"(?:once|when|after)\b"
        ),
        (
            r"\bkindly\s+let\s+me\s+know\s+"
            r"(?:once|when|after)\b"
        ),
        (
            r"\blet\s+us\s+know\s+"
            r"(?:once|when|after)\b"
        ),
    ]

    if not any(
        re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )
        for pattern in commitment_patterns
    ):
        return None

    if reference_time is None:
        reference_time = timezone.now()

    evidence_text = _extract_evidence(
        subject,
        body,
        commitment_patterns,
    )

    response_due_at = _extract_due_at(
        evidence_text,
        reference_time=reference_time,
    )

    return {
        "expected_from": _extract_email(
            evidence_text
        ),
        "evidence_text": evidence_text,
        "response_due_at": response_due_at,
    }
