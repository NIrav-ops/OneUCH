"""
Enterprise Graph Cache
"""

from datetime import timedelta

from django.utils import timezone

from context.constants import GRAPH_CACHE_TIMEOUT


class GraphCache:

    _cache = {}

    @classmethod
    def get(cls, key):

        item = cls._cache.get(key)

        if item is None:
            return None

        expires_at, value = item

        if timezone.now() > expires_at:

            cls.delete(key)

            return None

        return value

    @classmethod
    def set(cls, key, value):

        expires_at = timezone.now() + timedelta(
            seconds=GRAPH_CACHE_TIMEOUT,
        )

        cls._cache[key] = (
            expires_at,
            value,
        )

        return value

    @classmethod
    def delete(cls, key):

        cls._cache.pop(
            key,
            None,
        )

    @classmethod
    def clear(cls):

        cls._cache.clear()

    @classmethod
    def size(cls):

        return len(cls._cache)