"""
Enterprise Filtering Framework

Reusable filtering helpers
for all One UCH APIs.

This framework intentionally remains
ORM-agnostic and works with Django QuerySets.
"""


class EnterpriseFilter:

    """
    Base enterprise filter.
    """

    def apply(
        self,
        queryset,
        request,
    ):
        return queryset


class OrganizationFilter(EnterpriseFilter):

    """
    Filter by organization.
    """

    parameter = "organization"

    def apply(
        self,
        queryset,
        request,
    ):

        organization = request.query_params.get(
            self.parameter,
        )

        if organization:

            queryset = queryset.filter(
                organization_id=organization,
            )

        return queryset


class StatusFilter(EnterpriseFilter):

    parameter = "status"

    def apply(
        self,
        queryset,
        request,
    ):

        status = request.query_params.get(
            self.parameter,
        )

        if status:

            queryset = queryset.filter(
                status=status,
            )

        return queryset


class SearchFilter(EnterpriseFilter):

    """
    Simple icontains search.

    APIs specify searchable_fields.
    """

    parameter = "search"

    searchable_fields = []

    def apply(
        self,
        queryset,
        request,
    ):

        keyword = request.query_params.get(
            self.parameter,
        )

        if (
            not keyword
            or not self.searchable_fields
        ):
            return queryset

        from django.db.models import Q

        query = Q()

        for field in self.searchable_fields:

            query |= Q(
                **{
                    f"{field}__icontains": keyword,
                }
            )

        return queryset.filter(query)