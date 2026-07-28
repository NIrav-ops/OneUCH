import redis
from django.conf import settings

redis_client = redis.Redis.from_url(settings.CELERY_BROKER_URL)


def acquire_sync_lock(account_id, timeout=60):

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