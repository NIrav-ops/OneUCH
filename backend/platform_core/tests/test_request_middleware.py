from django.http import HttpResponse
from django.test import RequestFactory
from django.test import TestCase

from platform_core.context.middleware import (
    RequestContextMiddleware,
)

from platform_core.context import (
    current_request_id,
)


class RequestMiddlewareTests(TestCase):

    def test_request_context_created(self):

        factory = RequestFactory()

        request = factory.get("/")

        def response(req):

            self.assertIsNotNone(
                current_request_id(),
            )

            return HttpResponse("OK")

        middleware = RequestContextMiddleware(
            response,
        )

        result = middleware(
            request,
        )

        self.assertEqual(
            result.status_code,
            200,
        )

    def test_headers_added(self):

        factory = RequestFactory()

        request = factory.get("/")

        middleware = RequestContextMiddleware(
            lambda req: HttpResponse("OK"),
        )

        response = middleware(
            request,
        )

        self.assertIn(
            "X-Request-ID",
            response,
        )

        self.assertIn(
            "X-Execution-Time",
            response,
        )