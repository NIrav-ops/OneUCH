from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from inbox.models import InboxMessage
from ai.providers.simple_ai import SimpleAIProvider


class AIConversationSummaryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        messages = InboxMessage.objects.filter(
            conversation_id=conversation_id,
            user=request.user
        ).order_by("received_at")

        text = "\n".join(m.body for m in messages)

        ai = SimpleAIProvider()
        response = ai.generate(
            f"Summarize this email conversation:\n{text}"
        )

        return Response({
            "summary": response.text
        })
