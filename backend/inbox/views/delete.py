from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

import imaplib
from inbox.models import InboxMessage
from email_accounts.models import EmailAccount


class DeleteMessageAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, message_id):

        try:
            message = InboxMessage.objects.get(
                id=message_id,
                user=request.user
            )
        except InboxMessage.DoesNotExist:
            return Response({"error": "Message not found"}, status=404)

        email_account = EmailAccount.objects.filter(
            user=request.user,
            is_active=True
        ).first()

        if not email_account:
            return Response({"error": "No active email account"}, status=400)

        password = request.data.get("password")
        if not password:
            return Response({"error": "Password required"}, status=400)

        mail = imaplib.IMAP4_SSL(
            email_account.imap_server,
            email_account.imap_port
        )
        mail.login(email_account.email_address, password)

        # Extract real UID
        uid = message.external_message_id.split("_")[-1]

        # Select All Mail
        mail.select('"[Gmail]/All Mail"')

        # Move to Trash using Gmail label system
        mail.uid("STORE", uid, "+X-GM-LABELS", "(\\Trash)")

        # Optional: remove Inbox label if needed
        mail.uid("STORE", uid, "-X-GM-LABELS", "(\\Inbox)")

        mail.logout()

        # Soft delete in DB (better approach)
        message.folder = "trash"
        message.save()

        return Response({"status": "deleted"})