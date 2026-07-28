from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from platform_core.context.middleware import (
    RequestContextMiddleware,
)


class CorrelationContextTests(TestCase):

    def test_generated(self):

        request = RequestFactory().get("/")

        middleware = RequestContextMiddleware(
            lambda req: HttpResponse()
        )

        response = middleware(request)

        self.assertIn(
            "X-Correlation-ID",
            response,
        )

    def test_preserved(self):

        request = RequestFactory().get(
            "/",
            HTTP_X_CORRELATION_ID="abc123",
        )

        middleware = RequestContextMiddleware(
            lambda req: HttpResponse()
        )

        response = middleware(request)

        self.assertEqual(

            response["X-Correlation-ID"],

            "abc123",

        )