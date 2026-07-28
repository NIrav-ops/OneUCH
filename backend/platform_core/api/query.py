"""
Enterprise Query Framework

One UCH Enterprise Platform

Provides reusable query helpers for all
services and APIs.

Goals

✓ Organization aware

✓ Active object filtering

✓ Search ready

✓ Future RBAC

✓ Multi-tenant ready
"""

from django.db.models import QuerySet


class EnterpriseQuery:

    """
    Base query helper.
    """

    @staticmethod
    def all(queryset: QuerySet):

        if not hasattr(queryset, "all"):
            return queryset

        return queryset.all()

    @staticmethod
    def active(
        queryset: QuerySet,
    ):

        if not hasattr(queryset, "model"):
            return queryset

        if hasattr(
            queryset.model,
            "status",
        ):

            return queryset.filter(
                status="active",
            )

        return queryset

    @staticmethod
    def organization(
        queryset: QuerySet,
        organization,
    ):

        if not hasattr(queryset, "model"):
            return queryset

        if hasattr(
            queryset.model,
            "organization",
        ):

            return queryset.filter(
                organization=organization,
            )

        return queryset

    @staticmethod
    def by_id(
        queryset: QuerySet,
        pk,
    ):

        if not hasattr(queryset, "filter"):
            return queryset

        return queryset.filter(
            pk=pk,
        )

    @staticmethod
    def search(
        queryset: QuerySet,
        field,
        value,
    ):

        if not hasattr(queryset, "filter"):
            return queryset

        return queryset.filter(
            **{
                f"{field}__icontains": value,
            }
        )
    
class QueryPipeline:

    """
    Enterprise Query Pipeline

    Allows multiple query helpers
    to be chained together.
    """

    def __init__(
        self,
        queryset,
    ):

        self.queryset = queryset

    def active(self):

        self.queryset = EnterpriseQuery.active(
            self.queryset,
        )

        return self

    def organization(
        self,
        organization,
    ):

        self.queryset = EnterpriseQuery.organization(
            self.queryset,
            organization,
        )

        return self

    def search(
        self,
        field,
        value,
    ):

        self.queryset = EnterpriseQuery.search(
            self.queryset,
            field,
            value,
        )

        return self

    def get(self):

        return self.queryset