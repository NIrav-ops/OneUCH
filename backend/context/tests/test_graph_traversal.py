from django.test import TestCase

from inbox.models import Organization

from context.models import (
    BusinessObject,
    BusinessObjectType,
    BusinessRelationship,
)

from context.services.graph_traversal import (
    GraphTraversalService,
)


class GraphTraversalTests(TestCase):

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

        self.infosys = BusinessObject.objects.create(
            organization=self.organization,
            object_type=self.object_type,
            name="Infosys",
            status="active",
        )

        self.amazon = BusinessObject.objects.create(
            organization=self.organization,
            object_type=self.object_type,
            name="Amazon",
            status="active",
        )

        BusinessRelationship.objects.create(
            source_object=self.google,
            target_object=self.microsoft,
        )

        BusinessRelationship.objects.create(
            source_object=self.microsoft,
            target_object=self.infosys,
        )

        self.service = GraphTraversalService()

    def test_bfs_depth_1(self):

        results = self.service.bfs(
            start_object=self.google,
            max_depth=1,
        )

        self.assertEqual(
            len(results),
            2,
        )

    def test_bfs_depth_2(self):

        results = self.service.bfs(
            start_object=self.google,
            max_depth=2,
        )

        self.assertEqual(
            len(results),
            3,
        )

    def test_bfs_none(self):

        results = self.service.bfs(
            start_object=None,
        )

        self.assertEqual(
            len(results),
            0,
        )
    
    def test_dfs_depth_1(self):

        results = self.service.dfs(
            start_object=self.google,
            max_depth=1,
        )

        self.assertEqual(
            len(results),
            2,
        )

    def test_dfs_depth_2(self):

        results = self.service.dfs(
            start_object=self.google,
            max_depth=2,
        )

        self.assertEqual(
            len(results),
            3,
        )

    def test_dfs_none(self):

        results = self.service.dfs(
            start_object=None,
        )

        self.assertEqual(
            len(results),
            0,
        )
    def test_path_exists(self):

        self.assertTrue(

            self.service.path_exists(

                start_object=self.google,

                target_object=self.infosys,

            )

        )

    def test_path_not_exists(self):

        self.assertFalse(

            self.service.path_exists(

                start_object=self.google,

                target_object=self.amazon,

            )

        )

    def test_path_same_object(self):

        self.assertTrue(

            self.service.path_exists(

                start_object=self.google,

                target_object=self.google,

            )

        )
    
    def test_shortest_path(self):

        path = self.service.shortest_path(

            start_object=self.google,

            target_object=self.infosys,

        )

        self.assertEqual(

            len(path),

            3,

        )

        self.assertEqual(

            path[0].name,

            "Google",

        )

        self.assertEqual(

            path[1].name,

            "Microsoft",

        )

        self.assertEqual(

            path[2].name,

            "Infosys",

        )


    def test_shortest_path_same_object(self):

        path = self.service.shortest_path(

            start_object=self.google,

            target_object=self.google,

        )

        self.assertEqual(

            len(path),

            1,

        )


    def test_shortest_path_not_found(self):

        path = self.service.shortest_path(

            start_object=self.google,

            target_object=self.amazon,

        )

        self.assertEqual(

            len(path),

            0,

        )   

    def test_distance(self):

        self.assertEqual(

            self.service.distance(

                start_object=self.google,

                target_object=self.infosys,

            ),

            2,

        )


    def test_distance_same_object(self):

        self.assertEqual(

            self.service.distance(

                start_object=self.google,

                target_object=self.google,

            ),

            0,

        )


    def test_distance_not_found(self):

        self.assertEqual(

            self.service.distance(

                start_object=self.google,

                target_object=self.amazon,

            ),

            -1,

        )


    def test_reachable_objects(self):

        reachable = self.service.reachable_objects(

            start_object=self.google,

            max_depth=2,

        )

        self.assertEqual(

            len(reachable),

            2,

        )

        self.assertEqual(

            reachable[0].name,

            "Microsoft",

        )

        self.assertEqual(

            reachable[1].name,

            "Infosys",

        )


    def test_reachable_none(self):

        reachable = self.service.reachable_objects(

            start_object=None,

        )

        self.assertEqual(

            len(reachable),

            0,

        )   

    def test_multiple_calls_consistent(self):

        first = self.service.shortest_path(
            start_object=self.google,
            target_object=self.infosys,
        )

        second = self.service.shortest_path(
            start_object=self.google,
            target_object=self.infosys,
        )

        self.assertEqual(
            len(first),
            len(second),
        )


    def test_reachable_repeatable(self):

        first = self.service.reachable_objects(
            start_object=self.google,
            max_depth=2,
        )

        second = self.service.reachable_objects(
            start_object=self.google,
            max_depth=2,
        )

        self.assertEqual(
            len(first),
            len(second),
        )        