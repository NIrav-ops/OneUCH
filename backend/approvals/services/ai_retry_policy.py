from datetime import timedelta

from django.utils import timezone


def calculate_ai_retry(
    *,
    attempt_count: int,
    max_attempts: int,
    base_seconds: int,
    max_seconds: int,
    now=None,
):
    if now is None:
        now = timezone.now()

    attempt_count = max(
        int(attempt_count),
        1,
    )

    max_attempts = max(
        int(max_attempts),
        1,
    )

    if attempt_count >= max_attempts:
        return {
            "status": "failed",
            "next_retry_at": None,
        }

    delay_seconds = (
        int(base_seconds)
        * (
            3
            ** (
                attempt_count
                - 1
            )
        )
    )

    delay_seconds = min(
        delay_seconds,
        int(max_seconds),
    )

    return {
        "status": "retry_wait",
        "next_retry_at": (
            now
            + timedelta(
                seconds=delay_seconds
            )
        ),
    }


def can_attempt_ai_analysis(
    state,
    *,
    now=None,
) -> bool:
    if state is None:
        return True

    if state.status == "failed":
        return False

    if now is None:
        now = timezone.now()

    if state.next_retry_at is None:
        return True

    return (
        state.next_retry_at
        <= now
    )