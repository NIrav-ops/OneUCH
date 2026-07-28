from django.test import TestCase

from context.services.graph_traversal import (
    GraphTraversalService,
)

from context.services.graph_repository import (
    GraphRepository,
)

from context.exceptions import (
    BusinessObjectNotFound,
    RelationshipError,
)

from context.services.relationship_repository import (
    RelationshipRepository,
)

from inbox.models import Organization
from context.models import (
    BusinessObject,
    BusinessObjectType,
)


class GraphExceptionTests(TestCase):

    def setUp(self):

        self.service = GraphTraversalService()

        self.repo = GraphRepository()

        self.relationship_repo = RelationshipRepository()

        organization = Organization.objects.create(
            name="Test Org",
        )

        object_type = BusinessObjectType.objects.create(
            name="Company",
        )

        self.google = BusinessObject.objects.create(
            organization=organization,
            object_type=object_type,
            name="Google",
            status="active",
        )

    def test_neighbors_none(self):

        with self.assertRaises(
            BusinessObjectNotFound,
        ):

            self.repo.neighbors(None)

    def test_same_relationship(self):

        with self.assertRaises(
            RelationshipError,
        ):

            self.relationship_repo.create_relationship(

                source_object=self.google,

                target_object=self.google,

            )