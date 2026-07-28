from platform_core.api.permissions import (EnterprisePermission,)
from rest_framework.views import APIView

from platform_core.api.response import APIResponse

from platform_core.api.status import (
    MESSAGE_SUCCESS,
)

from platform_core.api.pagination import (
    EnterprisePagination,
)

from platform_core.api.filters import (
    EnterpriseFilter,
)

from platform_core.api.ordering import (
    EnterpriseOrdering,
)

class EnterpriseAPIView(APIView):
    """
    Base API View for One UCH.

    Every API endpoint should inherit
    from this class.

    Responsibilities:

    • Authentication

    • Standard Response

    • Future Logging

    • Future Metrics

    • Future Tracing

    • Future Audit

    """

    permission_classes = [EnterprisePermission,]
    
    pagination_class = EnterprisePagination

    filter_backends = []

    ordering_backend = None

    def success(

        self,

        *,

        data=None,

        message=MESSAGE_SUCCESS,

    ):

        return APIResponse.build(

            success=True,

            message=message,

            data=data,

        )

    def failure(

        self,

        *,

        message,

        errors=None,

        status_code=400,

    ):

        return APIResponse.build(

            success=False,

            message=message,

            errors=errors,

            status_code=status_code,

        )
    
    def paginate(

        self,

        queryset,

        request,

        serializer,

    ):

        paginator = self.pagination_class()

        page = paginator.paginate_queryset(

            queryset,

            request,

            view=self,

        )

        if page is None:

            return self.success(

                data=serializer(

                    queryset,

                    many=True,

                ).data

            )

        return paginator.get_paginated_response(

            serializer(

                page,

                many=True,

            ).data

        )
    
    def forbidden(

        self,

        message="Permission denied.",

    ):

        return self.failure(

            message=message,

            status_code=403,

        )


    def unauthorized(

        self,

        message="Authentication required.",

    ):

        return self.failure(

            message=message,

            status_code=401,

        )


    def not_found(

        self,

        message="Resource not found.",

    ):

        return self.failure(

            message=message,

            status_code=404,

        )


    def bad_request(

        self,

        message="Invalid request.",

        errors=None,

    ):

        return self.failure(

            message=message,

            errors=errors,

            status_code=400,

        )
    
    def filter_queryset(
        self,
        queryset,
        request,
    ):

        for backend in self.filter_backends:

            queryset = backend().apply(

                queryset,

                request,

            )

        return queryset
    
    def order_queryset(
        self,
        queryset,
        request,
    ):

        if self.ordering_backend is None:

            return queryset

        return self.ordering_backend().apply(

            queryset,

            request,

        )