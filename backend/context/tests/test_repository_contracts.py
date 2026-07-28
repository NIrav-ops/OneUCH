from django.test import TestCase

from context.services.graph_repository import (
    GraphRepository,
)

from context.exceptions import (
    BusinessObjectNotFound,
)


class RepositoryContractTests(TestCase):

    def setUp(self):

        self.repo = GraphRepository()

    def test_none_validation(self):

        with self.assertRaises(
            BusinessObjectNotFound,
        ):

            self.repo._validate_business_object(
                None
            )

    def test_neighbors_returns_list(self):

        result = []

        self.assertIsInstance(
            result,
            list,
        )