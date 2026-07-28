"""
Execution Context helpers.
"""

from platform_core.context import (
    get_request_context,
)


class ExecutionContext:

    @staticmethod
    def current():

        return get_request_context()

    @staticmethod
    def request_id():

        context = get_request_context()

        return (
            context.request_id
            if context
            else None
        )

    @staticmethod
    def correlation_id():

        context = get_request_context()

        return (
            context.correlation_id
            if context
            else None
        )