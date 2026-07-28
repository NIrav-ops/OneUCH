from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from inbox.models import InboxMessage
from ai.providers.simple_ai import SimpleAIProvider
from ai.prompt_builder import build_reply_prompt


class AISmartReplyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):
        tone = request.data.get("tone", "professional")

        messages = InboxMessage.objects.filter(
            conversation_id=conversation_id,
            user=request.user
        ).order_by("-received_at")[:5]

        messages = list(reversed(messages))

        prompt = build_reply_prompt(messages, tone=tone)

        ai = SimpleAIProvider()
        response = ai.generate(prompt)

        return Response({
            "suggested_reply": response.text,
            "tone": tone
        })
