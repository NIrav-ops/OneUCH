from unittest.mock import (
    Mock,
    patch,
)

from django.test import (
    SimpleTestCase,
)

from inbox.utils.sync_lock import (
    acquire_sync_lock,
    release_sync_lock,
)


class SyncLockTests(
    SimpleTestCase
):

    @patch(
        "inbox.utils.sync_lock.redis_client"
    )
    def test_acquire_uses_bounded_pilot_timeout(
        self,
        redis_client,
    ):
        lock = Mock()

        lock.acquire.return_value = (
            True
        )

        redis_client.lock.return_value = (
            lock
        )

        result = acquire_sync_lock(
            42
        )

        redis_client.lock.assert_called_once_with(
            "email_sync_lock:42",
            timeout=900,
        )

        lock.acquire.assert_called_once_with(
            blocking=False
        )

        self.assertIs(
            result,
            lock,
        )

    @patch(
        "inbox.utils.sync_lock.redis_client"
    )
    def test_acquire_returns_none_when_lock_is_already_active(
        self,
        redis_client,
    ):
        lock = Mock()

        lock.acquire.return_value = (
            False
        )

        redis_client.lock.return_value = (
            lock
        )

        result = acquire_sync_lock(
            42
        )

        self.assertIsNone(
            result
        )

        lock.acquire.assert_called_once_with(
            blocking=False
        )

    def test_release_uses_the_acquired_lock_object(
        self,
    ):
        lock = Mock()

        release_sync_lock(
            lock
        )

        lock.release.assert_called_once_with()
