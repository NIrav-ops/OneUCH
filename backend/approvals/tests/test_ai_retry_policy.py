from datetime import (
    datetime,
    timedelta,
    timezone as dt_timezone,
)
from types import SimpleNamespace

from django.test import SimpleTestCase

from approvals.services.ai_retry_policy import (
    calculate_ai_retry,
    can_attempt_ai_analysis,
)


class ApprovalAIRetryPolicyTests(
    SimpleTestCase
):

    def setUp(self):
        self.now = datetime(
            2026,
            8,
            25,
            5,
            0,
            tzinfo=dt_timezone.utc,
        )

    def test_first_failure_schedules_retry(
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
                seconds=300
            ),
        )

    def test_second_failure_uses_longer_delay(
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
            result["status"],
            "retry_wait",
        )

        self.assertEqual(
            result["next_retry_at"],
            self.now
            + timedelta(
                seconds=900
            ),
        )

    def test_final_failure_becomes_failed(
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

    def test_retry_delay_is_capped(
        self,
    ):
        result = calculate_ai_retry(
            attempt_count=4,
            max_attempts=10,
            base_seconds=300,
            max_seconds=1000,
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
                seconds=1000
            ),
        )

    def test_failed_state_cannot_retry(
        self,
    ):
        state = SimpleNamespace(
            status="failed",
            next_retry_at=None,
        )

        self.assertFalse(
            can_attempt_ai_analysis(
                state,
                now=self.now,
            )
        )

    def test_expired_retry_wait_can_retry(
        self,
    ):
        state = SimpleNamespace(
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
