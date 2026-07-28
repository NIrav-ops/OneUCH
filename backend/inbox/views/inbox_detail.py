from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from inbox.billing.utils import check_usage_limit, UsageLimitExceeded

from inbox.models import InboxMessage, UsageEvent
from inbox.serializers import InboxMessageSerializer


class InboxMessageDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, message_id):
        # 1️⃣ Fetch message
        try:
            message = InboxMessage.objects.get(
                id=message_id,
                user=request.user,
            )
        except InboxMessage.DoesNotExist:
            return Response(
                {"error": "Message not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        # 🔥 Mark as read only for inbound
        if not message.is_read:
            message.is_read = True
            message.save(update_fields=["is_read"])

        # 2️⃣ Get organization membership (FIX)
        membership = getattr(request.user, "organization_membership", None)
        if membership:
            try:
                membership = request.user.organization_membership
                check_usage_limit(
                organization=membership.organization,
                event_type="MESSAGE_VIEW",
                    )
            except UsageLimitExceeded as e:
                return Response(
            {"error": str(e)},
            status=403,
        )      
                  
        UsageEvent.objects.create(
                organization=membership.organization,
                user=request.user,
                event_type="MESSAGE_VIEW",
                metadata={
                    "message_id": message.id,
                },
            )

        # 3️⃣ Serialize response
        serializer = InboxMessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_200_OK)

        
