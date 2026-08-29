from rest_framework import (
    status,
)
from rest_framework.permissions import (
    IsAuthenticated,
)
from rest_framework.response import (
    Response,
)
from rest_framework.views import (
    APIView,
)

from inbox.models import (
    OrganizationUser,
)

from knowledge.services.commitments import (
    CommitmentsService,
)


class CommitmentsAPIView(APIView):
    """
    Organization-scoped read-only Commitment Ledger API.

    Fail closed when the authenticated user does not belong
    to an active organization.
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
            CommitmentsService
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
