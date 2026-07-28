"""
Enterprise Graph Cache Manager

Current:
    In-Memory GraphCache

Future:
    Redis
    Memcached
    Distributed Cache
"""

from context.services.graph_cache import GraphCache


class GraphCacheManager:

    @staticmethod
    def get(key):

        return GraphCache.get(key)

    @staticmethod
    def set(key, value):

        return GraphCache.set(
            key,
            value,
        )

    @staticmethod
    def delete(key):

        GraphCache.delete(key)

    @staticmethod
    def clear():

        GraphCache.clear()

    @staticmethod
    def size():

        return GraphCache.size()