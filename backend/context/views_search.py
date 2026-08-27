from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from platform_core.api.tenant import get_scoped_organization_or_404

from knowledge.services.search_service import SearchService
from context.serializers_search import SearchSerializer


class SearchAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id):
        organization = get_scoped_organization_or_404(
            request,
            organization_id,
        )

        query = request.GET.get("q", "")

        try:
            result = SearchService().search(
                organization=organization,
                query=query,
            )

            serializer = SearchSerializer(result)

            return Response(serializer.data)

        except Exception as exc:
            return Response(
                {"detail": str(exc)},
                status=500,
            )
