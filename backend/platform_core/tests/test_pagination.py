from django.test import TestCase

from rest_framework.test import APIRequestFactory

from platform_core.api.pagination import (
    EnterprisePagination,
)


class PaginationTests(TestCase):

    def setUp(self):

        self.factory = APIRequestFactory()

        self.pagination = EnterprisePagination()

    def test_default_page_size(self):

        self.assertEqual(

            self.pagination.page_size,

            20,

        )

    def test_max_page_size(self):

        self.assertEqual(

            self.pagination.max_page_size,

            100,

        )

    def test_query_parameter(self):

        self.assertEqual(

            self.pagination.page_query_param,

            "page",

        )

    def test_page_size_parameter(self):

        self.assertEqual(

            self.pagination.page_size_query_param,

            "page_size",

        )

    def test_last_page(self):

        self.assertEqual(

            self.pagination.last_page_strings,

            (

                "last",

            ),

        )