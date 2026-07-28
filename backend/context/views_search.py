from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from inbox.models import Organization

from knowledge.services.search_service import (
    SearchService,
)

from context.serializers_search import (
    SearchSerializer,
)


class SearchAPIView(APIView):

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

        query = request.GET.get(
            "q",
            "",
        )

        try:

            result = SearchService().search(

                organization=organization,

                query=query,

            )

            serializer = SearchSerializer(
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