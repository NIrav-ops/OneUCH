from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from inbox.models import Organization

from knowledge.services.workflow.intelligence import (
    WorkflowIntelligenceService,
)

from context.serializers_workflow import (
    WorkflowIntelligenceSerializer,
)


class WorkflowIntelligenceAPIView(APIView):

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

            result = WorkflowIntelligenceService().build(
                organization=organization,
            )

            serializer = WorkflowIntelligenceSerializer(
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