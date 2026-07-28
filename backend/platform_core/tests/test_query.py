from django.test import TestCase

from platform_core.api.query import (
    EnterpriseQuery,
    QueryPipeline,
)


class QueryFrameworkTests(TestCase):

    def test_query_exists(self):

        self.assertTrue(

            issubclass(

                EnterpriseQuery,

                object,

            )

        )

    def test_pipeline_exists(self):

        pipeline = QueryPipeline([])

        self.assertIsNotNone(

            pipeline,

        )

    def test_pipeline_get(self):

        pipeline = QueryPipeline([])

        self.assertEqual(

            pipeline.get(),

            [],

        )

    def test_pipeline_active(self):

        pipeline = QueryPipeline([])

        self.assertIs(

            pipeline.active(),

            pipeline,

        )

    def test_pipeline_search(self):

        pipeline = QueryPipeline([])

        self.assertIs(

            pipeline.search(

                "name",

                "john",

            ),

            pipeline,

        )

    def test_pipeline_org(self):

        pipeline = QueryPipeline([])

        self.assertIs(

            pipeline.organization(

                None,

            ),

            pipeline,

        )