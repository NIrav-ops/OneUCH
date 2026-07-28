from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import TimelineEvent
from .serializers import TimelineEventSerializer


class ConversationTimelineAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):

        events = TimelineEvent.objects.filter(
            conversation_id=conversation_id
        ).order_by("-created_at")

        serializer = TimelineEventSerializer(
            events,
            many=True
        )

        return Response(serializer.data)