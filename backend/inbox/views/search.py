from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from inbox.models import InboxMessage

from platform_core.api.tenant import (
    get_user_organization_or_404,
)


class MessageSearchAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        organization = (
            get_user_organization_or_404(
                request
            )
        )

        query = request.GET.get(
            "q",
            "",
        )

        messages = (
            InboxMessage.objects
            .filter(
                user=request.user,
                organization=organization,
                subject__icontains=query,
            )
            .order_by(
                "-received_at"
            )[:50]
        )

        data = [
            {
                "subject":
                    message.subject,

                "sender":
                    message.sender,

                "received_at":
                    message.received_at,
            }

            for message
            in messages
        ]

        return Response(
            data
        )
