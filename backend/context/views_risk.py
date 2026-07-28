from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from inbox.models import Organization

from knowledge.services.communication_intelligence import (
    CommunicationIntelligenceService,
)

from knowledge.services.risk.executive_risk import (
    ExecutiveRiskService,
)

from context.serializers_risk import (
    ExecutiveRiskSerializer,
)


class ExecutiveRiskAPIView(APIView):

    permission_classes = [
        IsAuthenticated,
    ]

    def get(
        self,
        request,
        organization_id,
    ):

        organization = get_object_or_404(
            Organization,
            pk=organization_id,
        )

        try:

            communication = (
                CommunicationIntelligenceService().build(
                    organization=organization,
                )
            )

            result = ExecutiveRiskService().build(
                organization=organization,
                communication=communication,
            )

            serializer = ExecutiveRiskSerializer(
                result,
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