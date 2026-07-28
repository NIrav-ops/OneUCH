from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from inbox.models import Conversation
from conversations.serializers import (
    ConversationListSerializer,
    ConversationDetailSerializer,
)


class ConversationListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        conversations = (
            Conversation.objects
            .filter(user=request.user)
            .order_by("-updated_at")
        )

        serializer = ConversationListSerializer(conversations, many=True)
        return Response(serializer.data)


class ConversationDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        conversation = get_object_or_404(
            Conversation,
            id=conversation_id,
            user=request.user
        )

        serializer = ConversationDetailSerializer(conversation)
        return Response(serializer.data)
