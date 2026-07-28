"""
Enterprise Request Bootstrap Middleware

Creates and manages the RequestContext
for every incoming HTTP request.
"""

from time import perf_counter

from platform_core import context
from platform_core.context.context_manager import (
    ContextManager,
)

from platform_core.context.request_context import (
    RequestContext,
)

from platform_core.context.organization import (
    OrganizationResolver,
)

from platform_core.context.tenant import (
    TenantResolver,
)

from platform_core.context.correlation import (
    Correlation,
)

from platform_core.context.security import (
    SecurityResolver,
)


class RequestContextMiddleware:

    """
    Bootstraps the request context.
    """

    def __init__(self, get_response):

        self.get_response = get_response

    def __call__(self, request):

        start = perf_counter()

        context = RequestContext.empty()

        context.correlation_id = (
            Correlation.resolve(
                request,
            )
        )

        context.user = getattr(
            request,
            "user",
            None,
        )

        context.organization = (

            OrganizationResolver.resolve(
                request,
            )

        )

        context.tenant = (
            TenantResolver.resolve(
                request,
            )
        )

        context.security = (
            SecurityResolver.resolve(
                request,
            )
        )

        context.ip_address = self._ip(request)

        context.user_agent = request.META.get(
            "HTTP_USER_AGENT",
        )

        context.path = request.path

        context.method = request.method

        ContextManager.push(
            context,
        )

        try:

            response = self.get_response(
                request,
            )

        finally:

            elapsed = (
                perf_counter() - start
            )

            response["X-Correlation-ID"] = (
                context.correlation_id
            )

            response["X-Request-ID"] = (
                context.request_id
            )

            response["X-Execution-Time"] = (
                f"{elapsed:.4f}s"
            )

            ContextManager.pop()

        return response

    def _ip(self, request):

        forwarded = request.META.get(
            "HTTP_X_FORWARDED_FOR",
        )

        if forwarded:

            return forwarded.split(",")[0].strip()

        return request.META.get(
            "REMOTE_ADDR",
        )