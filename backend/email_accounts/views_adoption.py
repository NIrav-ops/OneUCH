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

from email_accounts.services.adoption import (
    MailAdoptionService,
)

from inbox.models import (
    OrganizationUser,
)


class MailAdoptionAPIView(APIView):
    """
    Read-only governed mailbox adoption status.

    Supports OAuth-backed Gmail/Microsoft accounts and
    credential-backed Other Work Email without returning
    OAuth tokens or mailbox credentials.
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

        return Response(
            MailAdoptionService
            .build_payload(
                user=request.user,
                organization=(
                    membership.organization
                ),
            ),
            status=(
                status.HTTP_200_OK
            ),
        )
