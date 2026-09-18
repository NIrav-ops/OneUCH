from uuid import uuid4

import redis
from django.conf import settings

redis_client = redis.Redis.from_url(settings.CELERY_BROKER_URL)


BACKGROUND_MAILBOX_SYNC_LOCK_TIMEOUT_SECONDS = 7200


def acquire_sync_lock(account_id, timeout=900):

    lock_key = f"email_sync_lock:{account_id}"

    lock = redis_client.lock(lock_key, timeout=timeout)

    acquired = lock.acquire(blocking=False)

    return lock if acquired else None


def release_sync_lock(lock):

    if lock:
        try:
            lock.release()
        except Exception:
            pass

SYNC_DISPATCH_TIMEOUT_SECONDS = (
    BACKGROUND_MAILBOX_SYNC_LOCK_TIMEOUT_SECONDS
)


_SYNC_DISPATCH_RESERVE_SCRIPT = """
if redis.call("EXISTS", KEYS[1]) == 1 then
    return 0
end

if redis.call(
    "SET",
    KEYS[2],
    ARGV[1],
    "NX",
    "EX",
    ARGV[2]
) then
    return 1
end

return 0
"""


_SYNC_DISPATCH_RELEASE_SCRIPT = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
end

return 0
"""


def reserve_sync_dispatch(
    account_id,
    timeout=SYNC_DISPATCH_TIMEOUT_SECONDS,
):
    """
    Atomically reserve one scheduled mailbox dispatch.

    A mailbox is not scheduled when:
    - its runtime sync lock is already active, or
    - another scheduled dispatch is already reserved.
    """

    token = uuid4().hex

    acquired = redis_client.eval(
        _SYNC_DISPATCH_RESERVE_SCRIPT,
        2,
        f"email_sync_lock:{account_id}",
        f"email_sync_dispatch:{account_id}",
        token,
        int(timeout),
    )

    if not acquired:
        return None

    return token


def release_sync_dispatch(
    account_id,
    token,
):
    """
    Release only the dispatch reservation owned by this token.
    """

    if not token:
        return False

    try:
        released = redis_client.eval(
            _SYNC_DISPATCH_RELEASE_SCRIPT,
            1,
            f"email_sync_dispatch:{account_id}",
            str(token),
        )

    except Exception:
        # Reservation has a bounded TTL and must never turn
        # mailbox synchronization itself into a failure.
        return False

    return bool(released)
