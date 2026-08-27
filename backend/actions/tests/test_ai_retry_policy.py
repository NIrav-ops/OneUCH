from datetime import (
    datetime,
    timedelta,
    timezone as dt_timezone,
)

from django.test import SimpleTestCase

from actions.services.ai_retry_policy import (
    calculate_ai_retry,
    can_attempt_ai_analysis,
)


class DummyState:

    def __init__(
        self,
        *,
        status,
        next_retry_at=None,
    ):
        self.status = status
        self.next_retry_at = next_retry_at


class AIActionRetryPolicyTests(
    SimpleTestCase
):

    def setUp(self):
        self.now = datetime(
            2026,
            8,
            25,
            7,
            0,
            tzinfo=dt_timezone.utc,
        )

    def test_first_failure_waits_base_period(
        self,
    ):
        result = calculate_ai_retry(
            attempt_count=1,
            max_attempts=3,
            base_seconds=300,
            max_seconds=3600,
            now=self.now,
        )

        self.assertEqual(
            result["status"],
            "retry_wait",
        )

        self.assertEqual(
            result["next_retry_at"],
            self.now
            + timedelta(
                minutes=5
            ),
        )

    def test_second_failure_uses_backoff(
        self,
    ):
        result = calculate_ai_retry(
            attempt_count=2,
            max_attempts=3,
            base_seconds=300,
            max_seconds=3600,
            now=self.now,
        )

        self.assertEqual(
            result["next_retry_at"],
            self.now
            + timedelta(
                minutes=15
            ),
        )

    def test_max_attempt_marks_failed(
        self,
    ):
        result = calculate_ai_retry(
            attempt_count=3,
            max_attempts=3,
            base_seconds=300,
            max_seconds=3600,
            now=self.now,
        )

        self.assertEqual(
            result["status"],
            "failed",
        )

        self.assertIsNone(
            result["next_retry_at"]
        )

    def test_failed_state_cannot_retry(
        self,
    ):
        state = DummyState(
            status="failed",
        )

        self.assertFalse(
            can_attempt_ai_analysis(
                state,
                now=self.now,
            )
        )

    def test_future_retry_is_blocked(
        self,
    ):
        state = DummyState(
            status="retry_wait",
            next_retry_at=(
                self.now
                + timedelta(
                    minutes=5
                )
            ),
        )

        self.assertFalse(
            can_attempt_ai_analysis(
                state,
                now=self.now,
            )
        )

    def test_expired_retry_is_allowed(
        self,
    ):
        state = DummyState(
            status="retry_wait",
            next_retry_at=(
                self.now
                - timedelta(
                    seconds=1
                )
            ),
        )

        self.assertTrue(
            can_attempt_ai_analysis(
                state,
                now=self.now,
            )
        )
