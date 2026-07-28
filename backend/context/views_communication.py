from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from inbox.models import Organization

from knowledge.services.communication_intelligence import (
    CommunicationIntelligenceService,
)

from context.serializers_communication import (
    CommunicationIntelligenceSerializer,
)


class CommunicationIntelligenceAPIView(
    APIView,
):

    permission_classes = [
        IsAuthenticated,
    ]

    def get(
        self,
        request,
        organization_id,
    ):

        try:

            organization = Organization.objects.get(
                pk=organization_id,
            )

        except Organization.DoesNotExist:

            return Response(
                {
                    "detail": "Organization not found.",
                },
                status=404,
            )

        try:

            result = CommunicationIntelligenceService().build(
                organization=organization,
            )

            serializer = (
                CommunicationIntelligenceSerializer(
                    result,
                )
            )

            return Response(
                serializer.data,
            )

        except Exception as exc:

            return Response(
                {
                    "detail": str(exc),
                },
                status=500,
            )