from django.test import TestCase

from context.models import (
    BusinessObject,
    BusinessObjectType,
)

from inbox.models import Organization

from context.services.graph_repository import (
    GraphRepository,
)
from context.models import BusinessRelationship


class GraphRepositoryTests(TestCase):

    def setUp(self):

        self.organization = Organization.objects.create(
            name="Test Org",
        )

        self.object_type = BusinessObjectType.objects.create(
            name="Company",
        )

        self.google = BusinessObject.objects.create(
            organization=self.organization,
            object_type=self.object_type,
            name="Google",
            status="active",
        )

        self.microsoft = BusinessObject.objects.create(
            organization=self.organization,
            object_type=self.object_type,
            name="Microsoft",
            status="active",
        )

        BusinessRelationship.objects.create(
            source_object=self.google,
            target_object=self.microsoft,
        )

        self.amazon = BusinessObject.objects.create(
            organization=self.organization,
            object_type=self.object_type,
            name="Amazon",
            status="active",
        )

    def test_object_count(self):

        repo = GraphRepository()

        self.assertEqual(
            repo.object_count(),
            3,
        )

    def test_all_objects(self):

        repo = GraphRepository()

        self.assertEqual(
            repo.all_objects().count(),
            3,
        )

    def test_relationship_count(self):

        repo = GraphRepository()

        self.assertEqual(
            repo.relationship_count(),
            BusinessRelationship.objects.count(),
        )

    def test_outgoing_relationships(self):

        repo = GraphRepository()

        self.assertEqual(
            repo.outgoing_relationships(
                self.google
            ).count(),
            1,
        )


    def test_incoming_relationships(self):

        repo = GraphRepository()

        self.assertEqual(
            repo.incoming_relationships(
                self.microsoft
            ).count(),
            1,
        )


    def test_neighbors(self):

        repo = GraphRepository()

        neighbours = repo.neighbors(
            self.google
        )

        self.assertEqual(
            len(neighbours),
            1,
        )

        self.assertEqual(
            neighbours[0].name,
            "Microsoft",
        )

    def test_graph_statistics(self):

        repo = GraphRepository()

        stats = repo.graph_statistics()

        self.assertEqual(
            stats["objects"],
            3,
        )

        self.assertEqual(
            stats["relationships"],
            1,
        )


    def test_isolated_objects(self):

        BusinessObject.objects.create(
            organization=self.organization,
            object_type=self.object_type,
            name="Oracle",
            status="active",
        )

        repo = GraphRepository()

        isolated = repo.isolated_objects()

        names = {obj.name for obj in isolated}

        self.assertEqual(
            len(isolated),
            2,
        )

        self.assertIn("Amazon", names)

        self.assertIn("Oracle", names)