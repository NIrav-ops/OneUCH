from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from inbox.models import InboxMessage


class MarkAllReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        updated = InboxMessage.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True)

        return Response(
            {
                "status": "success",
                "marked_read": updated,
            },
            status=status.HTTP_200_OK,
        )
