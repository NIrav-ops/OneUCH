from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from inbox.models import Conversation

from .models import TimelineEvent
from .serializers import TimelineEventSerializer

from platform_core.api.tenant import (
    get_user_organization_or_404,
)


class ConversationTimelineAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(
        self,
        request,
        conversation_id,
    ):

        organization = (
            get_user_organization_or_404(
                request
            )
        )

        conversation = (
            Conversation.objects
            .filter(
                id=conversation_id,
                user=request.user,
                organization=organization,
            )
            .first()
        )

        if conversation is None:
            return Response(
                {
                    "error":
                        "Conversation not found"
                },
                status=404,
            )

        events = (
            TimelineEvent.objects
            .filter(
                conversation=conversation
            )
            .order_by(
                "-created_at"
            )
        )

        serializer = TimelineEventSerializer(
            events,
            many=True,
        )

        return Response(
            serializer.data
        )
