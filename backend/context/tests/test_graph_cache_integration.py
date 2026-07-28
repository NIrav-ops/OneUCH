from django.test import TestCase

from inbox.models import Organization

from context.models import (
    BusinessObject,
    BusinessObjectType,
)

from context.services.graph_repository import (
    GraphRepository,
)

from context.services.graph_cache import (
    GraphCache,
)


class GraphCacheIntegrationTests(TestCase):

    def setUp(self):

        GraphCache.clear()

        self.organization = Organization.objects.create(
            name="Test Org",
        )

        self.object_type = BusinessObjectType.objects.create(
            name="Company",
        )

        BusinessObject.objects.create(
            organization=self.organization,
            object_type=self.object_type,
            name="Google",
            status="active",
        )

        self.repo = GraphRepository()

    def tearDown(self):

        GraphCache.clear()

    def test_object_count_cached(self):

        first = self.repo.object_count()

        second = self.repo.object_count()

        self.assertEqual(first, second)

        self.assertGreater(
            GraphCache.size(),
            0,
        )

    def test_statistics_cached(self):

        first = self.repo.graph_statistics()

        second = self.repo.graph_statistics()

        self.assertEqual(first, second)