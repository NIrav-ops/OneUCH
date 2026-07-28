"""
Correlation ID utilities.
"""

from uuid import uuid4


class Correlation:

    HEADER = "HTTP_X_CORRELATION_ID"

    @classmethod
    def resolve(cls, request):

        correlation = request.META.get(
            cls.HEADER,
        )

        if correlation:

            return correlation

        return str(uuid4())