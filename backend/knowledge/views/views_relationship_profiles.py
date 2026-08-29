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

from knowledge.services.relationship_profiles import (
    RelationshipProfilesService,
)


class RelationshipProfilesAPIView(APIView):
    """
    Read-only tenant-scoped external relationship profiles.

    GET /api/knowledge/relationships/
        -> relationship index

    GET /api/knowledge/relationships/?email=x@example.com
        -> one detailed relationship profile
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

        organization = (
            membership.organization
        )

        email = (
            request.query_params
            .get(
                "email"
            )
        )

        if email:
            payload = (
                RelationshipProfilesService
                .build_profile(
                    organization=organization,
                    email=email,
                )
            )

            if payload is None:
                return Response(
                    {
                        "detail": (
                            "Relationship profile "
                            "not found."
                        )
                    },
                    status=(
                        status
                        .HTTP_404_NOT_FOUND
                    ),
                )

            return Response(
                payload,
                status=(
                    status
                    .HTTP_200_OK
                ),
            )

        payload = (
            RelationshipProfilesService
            .build_index(
                organization=organization
            )
        )

        return Response(
            payload,
            status=status.HTTP_200_OK,
        )
