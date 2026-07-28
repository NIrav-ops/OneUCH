from django.test import TestCase

from platform_core.api.filters import (
    EnterpriseFilter,
    OrganizationFilter,
    StatusFilter,
    SearchFilter,
)


class FilterTests(TestCase):

    def test_base_filter(self):

        self.assertTrue(

            issubclass(

                EnterpriseFilter,

                object,

            )

        )

    def test_org_filter(self):

        self.assertEqual(

            OrganizationFilter.parameter,

            "organization",

        )

    def test_status_filter(self):

        self.assertEqual(

            StatusFilter.parameter,

            "status",

        )

    def test_search_filter(self):

        self.assertEqual(

            SearchFilter.parameter,

            "search",

        )

    def test_search_fields_default(self):

        self.assertEqual(

            SearchFilter.searchable_fields,

            [],

        )