from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from platform_core.api.tenant import get_scoped_organization_or_404

from knowledge.services.communication_intelligence import (
    CommunicationIntelligenceService,
)
from knowledge.services.opportunity.executive_opportunity import (
    ExecutiveOpportunityService,
)
from context.serializers_opportunity import (
    ExecutiveOpportunitySerializer,
)


class ExecutiveOpportunityAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id):
        organization = get_scoped_organization_or_404(
            request,
            organization_id,
        )

        try:
            communication = CommunicationIntelligenceService().build(
                organization=organization,
            )

            result = ExecutiveOpportunityService().build(
                organization=organization,
                communication=communication,
            )

            serializer = ExecutiveOpportunitySerializer(
                result,
            )

            return Response(serializer.data)

        except Exception as exc:
            return Response(
                {"detail": str(exc)},
                status=500,
            )
