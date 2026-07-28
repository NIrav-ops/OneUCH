from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

from inbox.models import InboxMessage, Conversation
from inbox.tasks import send_email_task
from email_accounts.models import EmailAccount


class ReplyConversationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):

        body = request.data.get("body")
        password = request.data.get("password")

        if not body:
            return Response(
                {"error": "Reply body is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            conversation = Conversation.objects.get(
                id=conversation_id,
                user=request.user
            )
        except Conversation.DoesNotExist:
            return Response(
                {"error": "Conversation not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        latest_message = conversation.messages.order_by(
            "-received_at"
        ).first()

        if not latest_message:
            return Response(
                {"error": "No messages in conversation"},
                status=status.HTTP_400_BAD_REQUEST
            )

        override_account_id = request.data.get("email_account_id")

        if override_account_id:
            email_account = EmailAccount.objects.filter(
            id=override_account_id,
            user=request.user,
            is_active=True
            ).first()
        else:
        #Auto-detect from latest message
            email_account = latest_message.email_account

        if not email_account:
            return Response(
            {"error": "No valid email account found"},
            status=status.HTTP_400_BAD_REQUEST
        )

        subject = latest_message.subject
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"

        reply_message = InboxMessage.objects.create(
            user=request.user,
            organization=request.user.organization_membership.organization,
            platform=latest_message.platform,
            email_account=email_account,
            direction="outbound",
            external_message_id="pending",
            conversation=conversation,   # ✅ correct FK usage
            in_reply_to=latest_message.external_message_id,
            sender=email_account.email_address,
            recipients=latest_message.sender,
            subject=subject,
            body=body,
            received_at=timezone.now(),
            is_read=True,
            status="queued",
        )

        send_email_task.delay(
            email_account.id,
            latest_message.sender,
            subject,
            body,
            reply_message.id,
        )

        return Response(
            {"status": "Reply queued successfully"},
            status=status.HTTP_202_ACCEPTED
        )