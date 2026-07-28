import json
from datetime import datetime
from django.conf import settings

redis_client = settings.REDIS_CLIENT


def serialize_data(data):
    """
    Convert datetime to ISO format recursively
    """

    if isinstance(data, dict):
        return {k: serialize_data(v) for k, v in data.items()}

    elif isinstance(data, list):
        return [serialize_data(item) for item in data]

    elif isinstance(data, datetime):
        return data.isoformat()

    return data


def cache_conversations(user_id, conversations):
    key = f"inbox_cache_{user_id}"

    safe_data = serialize_data(conversations)

    redis_client.set(
        key,
        json.dumps(safe_data),
        ex=60
    )


def get_cached_conversations(user_id):
    key = f"inbox_cache_{user_id}"

    data = redis_client.get(key)

    if data:
        return json.loads(data)

    return None


def invalidate_conversation_cache(user_id):
    key = f"inbox_cache_{user_id}"
    redis_client.delete(key)