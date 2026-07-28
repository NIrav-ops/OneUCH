from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from django.utils import timezone

from .models import EmailAccount
from inbox.models import InboxMessage
from inbox.tasks import send_email_task

class SendEmailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # 1️⃣ Get active email account
        email_account = EmailAccount.objects.filter(
            user=request.user,
            is_active=True
        ).first()

        if not email_account:
            return Response(
                {"error": "No active email account"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Ensure SMTP password exists
        if not email_account.smtp_password:
            return Response(
                {"error": "SMTP app password not configured"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2️⃣ Extract request data
        to_email = request.data.get("to")
        subject = request.data.get("subject", "")
        body = request.data.get("body", "")

        if not to_email:
            return Response(
                {"error": "Recipient email is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3️⃣ Create queued inbox record
        inbox_message = InboxMessage.objects.create(
            user=request.user,
            organization=request.user.organization_membership.organization,
            platform="imap",
            direction="outbound",
            external_message_id="pending",
            sender=email_account.email_address,
            recipients=to_email,
            subject=subject,
            body=body,
            received_at=timezone.now(),
            is_read=True,
            status="queued",
        )

        # 4️⃣ Send asynchronously via Celery
        send_email_task.delay(
            email_account.id,
            to_email,
            subject,
            body,
            inbox_message.id,
        )

        return Response(
            {"status": "Email queued for sending"},
            status=status.HTTP_202_ACCEPTED
        )

class EmailAccountListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        accounts = EmailAccount.objects.filter(user=request.user)

        data = [
            {
                "id": acc.id,
                "email_address": acc.email_address,
                "account_type": acc.account_type,
            }
            for acc in accounts
        ]

        return Response(data)