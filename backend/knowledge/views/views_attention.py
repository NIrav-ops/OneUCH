from rest_framework import status
from rest_framework.permissions import (
    IsAuthenticated,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from inbox.models import OrganizationUser

from knowledge.services.attention import (
    AttentionService,
)


class AttentionAPIView(APIView):
    """
    Current organization-scoped accountability attention
    surface.

    Fail closed when the authenticated user does not have an
    active organization membership.
    """

    permission_classes = [
        IsAuthenticated
    ]

    def get(
        self,
        request,
    ):
        membership = (
            OrganizationUser.objects
            .select_related(
                "organization"
            )
            .filter(
                user=request.user,
                organization__is_active=True,
            )
            .first()
        )

        if membership is None:
            return Response(
                {
                    "detail": (
                        "Active organization "
                        "membership required."
                    )
                },
                status=(
                    status
                    .HTTP_403_FORBIDDEN
                ),
            )

        payload = (
            AttentionService
            .build_payload(
                organization=(
                    membership.organization
                )
            )
        )

        return Response(
            payload,
            status=status.HTTP_200_OK,
        )
