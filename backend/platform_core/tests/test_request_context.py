from django.test import TestCase

from platform_core.context import (
    ContextManager,
    RequestContext,
    current_request_id,
)


class RequestContextTests(TestCase):

    def tearDown(self):

        ContextManager.pop()

    def test_context_creation(self):

        context = RequestContext.empty()

        self.assertIsNotNone(

            context.request_id,

        )

    def test_push(self):

        context = RequestContext.empty()

        ContextManager.push(

            context,

        )

        self.assertEqual(

            current_request_id(),

            context.request_id,

        )

    def test_pop(self):

        context = RequestContext.empty()

        ContextManager.push(

            context,

        )

        ContextManager.pop()

        self.assertIsNone(

            current_request_id(),

        )

    def test_current(self):

        context = RequestContext.empty()

        ContextManager.push(

            context,

        )

        self.assertEqual(

            ContextManager.current(),

            context,

        )