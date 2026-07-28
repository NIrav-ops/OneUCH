from django.test import TestCase

from context.services.graph_cache_manager import (
    GraphCacheManager,
)


class GraphCacheManagerTests(TestCase):

    def tearDown(self):

        GraphCacheManager.clear()

    def test_set_get(self):

        GraphCacheManager.set(
            "x",
            100,
        )

        self.assertEqual(

            GraphCacheManager.get(
                "x",
            ),

            100,

        )

    def test_delete(self):

        GraphCacheManager.set(
            "x",
            1,
        )

        GraphCacheManager.delete("x")

        self.assertIsNone(

            GraphCacheManager.get("x")

        )

    def test_clear(self):

        GraphCacheManager.set("a", 1)

        GraphCacheManager.set("b", 2)

        GraphCacheManager.clear()

        self.assertEqual(

            GraphCacheManager.size(),

            0,

        )