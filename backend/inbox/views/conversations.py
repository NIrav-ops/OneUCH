from django.db.models import Count

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from inbox.models import InboxMessage
from inbox.serializers import InboxMessageSerializer

from platform_core.api.tenant import (
    get_user_organization_or_404,
)


class ConversationListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        organization = (
            get_user_organization_or_404(
                request
            )
        )

        conversations = (
            InboxMessage.objects
            .filter(
                user=request.user,
                organization=organization,
            )
            .exclude(
                conversation_id__isnull=True
            )
            .values(
                "conversation_id"
            )
            .annotate(
                total_messages=Count("id")
            )
            .order_by(
                "-total_messages"
            )
        )

        return Response(
            conversations
        )


class ConversationDetailAPIView(APIView):
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

        messages = (
            InboxMessage.objects
            .filter(
                user=request.user,
                organization=organization,
                conversation_id=conversation_id,
            )
            .order_by(
                "received_at"
            )
        )

        if not messages.exists():

            return Response(
                {
                    "error":
                        "Conversation not found"
                },
                status=(
                    status
                    .HTTP_404_NOT_FOUND
                ),
            )

        serializer = (
            InboxMessageSerializer(
                messages,
                many=True,
            )
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class MarkConversationReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(
        self,
        request,
        conversation_id,
    ):

        organization = (
            get_user_organization_or_404(
                request
            )
        )

        messages = InboxMessage.objects.filter(
            user=request.user,
            organization=organization,
            conversation_id=conversation_id,
        )

        if not messages.exists():

            return Response(
                {
                    "error":
                        "Conversation not found"
                },
                status=(
                    status
                    .HTTP_404_NOT_FOUND
                ),
            )

        messages.update(
            is_read=True
        )

        return Response(
            {
                "status":
                    "Conversation marked as read"
            },
            status=status.HTTP_200_OK,
        )
