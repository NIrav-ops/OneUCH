from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from inbox.models import Organization

from knowledge.services.executive_dashboard import (
    ExecutiveDashboardService,
)

from knowledge.services.ai.intelligence import (
    AIIntelligenceService,
)

from context.serializers_ai import (
    AIIntelligenceSerializer,
)


class AIIntelligenceAPIView(APIView):

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

            executive_dashboard = (
                ExecutiveDashboardService().build(
                    organization=organization,
                )
            )

            result = AIIntelligenceService().build(
                organization=organization,
                executive_dashboard=executive_dashboard,
            )

            serializer = AIIntelligenceSerializer(
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