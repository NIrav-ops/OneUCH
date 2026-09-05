from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from inbox.models import InboxMessage

from platform_core.api.tenant import (
    get_user_organization_or_404,
)


class MarkAllReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        organization = (
            get_user_organization_or_404(
                request
            )
        )

        updated = InboxMessage.objects.filter(
            user=request.user,
            organization=organization,
            is_read=False,
        ).update(
            is_read=True
        )

        return Response(
            {
                "status": "success",
                "marked_read": updated,
            },
            status=status.HTTP_200_OK,
        )
