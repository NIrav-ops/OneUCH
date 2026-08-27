from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from context.models import Person

from platform_core.api.tenant import get_user_organization_or_404

from knowledge.services.people360 import People360Service
from context.serializers_people360 import People360Serializer


class People360APIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, person_id):
        organization = get_user_organization_or_404(
            request
        )

        person = get_object_or_404(
            Person,
            pk=person_id,
            organization=organization,
        )

        try:
            result = People360Service().build(
                person=person,
            )

            serializer = People360Serializer(
                result,
            )

            return Response(serializer.data)

        except Exception as exc:
            return Response(
                {"detail": str(exc)},
                status=500,
            )
