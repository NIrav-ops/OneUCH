from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogListAPIView(APIView):
    permission_classes = [
        IsAuthenticated
    ]

    def get(self, request):

        logs = (
            AuditLog.objects
            .filter(
                user=request.user
            )
            .order_by(
                "-created_at"
            )[:100]
        )

        serializer = AuditLogSerializer(
            logs,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
