from django.test import TestCase

from context.services.graph_cache import (
    GraphCache,
)


class GraphCacheTests(TestCase):

    def tearDown(self):

        GraphCache.clear()

    def test_set(self):

        GraphCache.set(
            "google",
            123,
        )

        self.assertEqual(

            GraphCache.get(
                "google",
            ),

            123,

        )

    def test_delete(self):

        GraphCache.set(
            "x",
            10,
        )

        GraphCache.delete("x")

        self.assertIsNone(

            GraphCache.get(
                "x",
            )

        )

    def test_clear(self):

        GraphCache.set("a", 1)

        GraphCache.set("b", 2)

        GraphCache.clear()

        self.assertEqual(

            GraphCache.size(),

            0,

        )

    def test_size(self):

        GraphCache.set("a", 1)

        GraphCache.set("b", 2)

        self.assertEqual(

            GraphCache.size(),

            2,

        )