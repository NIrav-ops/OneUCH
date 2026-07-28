"""
Enterprise API Mixins

Reusable API behaviours for the entire
One UCH platform.

These mixins intentionally avoid inheriting
from DRF GenericAPIView so that they work
with EnterpriseAPIView.

Future modules:

✓ Inbox

✓ Customer360

✓ Workflow

✓ Search

✓ AI

✓ Executive Dashboard
"""

from django.shortcuts import get_object_or_404


class ListMixin:

    """
    Enterprise List Behaviour
    """

    serializer_class = None

    def list(
        self,
        request,
        queryset,
    ):

        return self.paginate(

            queryset,

            request,

            self.serializer_class,

        )


class RetrieveMixin:

    """
    Enterprise Retrieve Behaviour
    """

    serializer_class = None

    lookup_field = "pk"

    def retrieve(

        self,

        request,

        queryset,

        value,

    ):

        instance = get_object_or_404(

            queryset,

            **{

                self.lookup_field: value,

            }

        )

        serializer = self.serializer_class(

            instance,

        )

        return self.success(

            message="Resource retrieved successfully.",

            data=serializer.data,

        )


class CreateMixin:

    """
    Enterprise Create Behaviour
    """

    serializer_class = None

    def create(

        self,

        request,

    ):

        serializer = self.serializer_class(

            data=request.data,

        )

        serializer.is_valid(

            raise_exception=True,

        )

        serializer.save()

        return self.success(

            message="Resource created successfully.",

            data=serializer.data,

        )


class UpdateMixin:

    """
    Enterprise Update Behaviour
    """

    serializer_class = None

    lookup_field = "pk"

    def update(

        self,

        request,

        queryset,

        value,

    ):

        instance = get_object_or_404(

            queryset,

            **{

                self.lookup_field: value,

            }

        )

        serializer = self.serializer_class(

            instance,

            data=request.data,

            partial=True,

        )

        serializer.is_valid(

            raise_exception=True,

        )

        serializer.save()

        return self.success(

            message="Resource updated successfully.",

            data=serializer.data,

        )


class DeleteMixin:

    """
    Enterprise Delete Behaviour
    """

    lookup_field = "pk"

    def destroy(

        self,

        queryset,

        value,

    ):

        instance = get_object_or_404(

            queryset,

            **{

                self.lookup_field: value,

            }

        )

        instance.delete()

        return self.success(

            message="Resource deleted successfully.",

            data=None,

        )