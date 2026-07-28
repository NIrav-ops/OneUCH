"""
Context Manager
"""

from platform_core.context.request_store import (
    RequestStore,
)


class ContextManager:

    @staticmethod
    def push(context):

        RequestStore.set(context)

    @staticmethod
    def pop():

        RequestStore.clear()

    @staticmethod
    def current():

        return RequestStore.get()