from django.test import TestCase

from context.services.graph_repository import (
    GraphRepository,
)

from context.services.base_graph_repository import (
    BaseGraphRepository,
)


class GraphInterfaceTests(TestCase):

    def test_repository_is_base_repository(self):

        repo = GraphRepository()

        self.assertIsInstance(
            repo,
            BaseGraphRepository,
        )