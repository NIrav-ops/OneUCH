from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from platform_core.api.tenant import (
    get_scoped_organization_or_404,
)

from knowledge.services.organization360 import (
    Organization360Service,
)

from context.serializers_organization360 import (
    Organization360Serializer,
)


class Organization360APIView(APIView):

    permission_classes = [
        IsAuthenticated,
    ]

    def get(
        self,
        request,
        organization_id,
    ):

        organization = (
            get_scoped_organization_or_404(
                request,
                organization_id,
            )
        )

        try:

            result = (
                Organization360Service()
                .build(
                    organization=organization,
                )
            )

            serializer = (
                Organization360Serializer(
                    result
                )
            )

            return Response(
                serializer.data
            )

        except Exception as exc:

            return Response(
                {
                    "detail": str(exc),
                },
                status=500,
            )
