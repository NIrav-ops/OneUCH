from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from context.models import BusinessObject

from context.services.customer360 import (
    Customer360Service,
)

from context.serializers import (
    Customer360Serializer,
)
from django.shortcuts import get_object_or_404

class Customer360APIView(APIView):

    permission_classes = [
        IsAuthenticated,
    ]

    

    def get(
        self,
        request,
        business_object_id,
    ):

        business_object = get_object_or_404(
            BusinessObject,
            pk=business_object_id,
        )

        try:

            result = Customer360Service().build(
                business_object=business_object,
            )

            result["business_object"] = {
                "id": business_object.id,
                "name": business_object.name,
                "status": business_object.status,
                "object_type": business_object.object_type.name,
            }

            serializer = Customer360Serializer(result)

            return Response(serializer.data)

        except Exception as exc:

            return Response(
                {
                    "detail": str(exc),
                },
                status=500,
            )