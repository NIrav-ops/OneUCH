"""
Enterprise Pagination Framework

One UCH Enterprise Platform

This pagination class is used by every
REST API endpoint that returns lists.

Goals

✓ Standard response

✓ Configurable page size

✓ React compatible

✓ Mobile compatible

✓ Future Cursor Pagination
"""

from collections import OrderedDict

from rest_framework.pagination import PageNumberPagination

from rest_framework.response import Response

from platform_core.api.metadata import (
    ResponseMetadata,
)


class EnterprisePagination(PageNumberPagination):

    """
    Standard pagination for One UCH.
    """

    page_size = 20

    page_size_query_param = "page_size"

    max_page_size = 100

    page_query_param = "page"

    last_page_strings = (
        "last",
    )

    def get_paginated_response(
        self,
        data,
    ):

        return Response(

            OrderedDict(

                [

                    (

                        "success",

                        True,

                    ),

                    (

                        "message",

                        "Data retrieved successfully.",

                    ),

                    (

                        "data",

                        data,

                    ),

                    (

                        "errors",

                        [],

                    ),

                    (
                        "meta",

                        ResponseMetadata.build(

                            pagination={

                                "page": self.page.number,

                                "page_size": self.get_page_size(

                                    self.request,

                                ),

                                "total_pages": self.page.paginator.num_pages,

                                "total_records": self.page.paginator.count,

                                "has_next": self.page.has_next(),

                                "has_previous": self.page.has_previous(),

                                "next": self.get_next_link(),

                                "previous": self.get_previous_link(),

                            }

                        ),

                    ),

                ]

            )

        )