from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from inbox.models import Conversation, InboxMessage


class MarkConversationReadAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):

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

        messages = InboxMessage.objects.filter(
            conversation=conversation,
            user=request.user,
            is_read=False
        )

        updated = messages.update(is_read=True)

        conversation.unread_count = 0
        conversation.save(update_fields=["unread_count"])

        return Response(
            {
                "status": "conversation marked as read",
                "updated": updated,
            },
            status=status.HTTP_200_OK
        )
    
import imaplib

from inbox.models import InboxMessage
from email_accounts.models import EmailAccount


class DeleteConversationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):

        messages = InboxMessage.objects.filter(
            user=request.user,
            conversation_id=conversation_id
        )

        if not messages.exists():
            return Response(
                {"error": "Conversation not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        email_account = EmailAccount.objects.filter(
            user=request.user,
            is_active=True
        ).first()

        if not email_account:
            return Response(
                {"error": "No active email account"},
                status=status.HTTP_400_BAD_REQUEST
            )

        password = request.data.get("password")
        if not password:
            return Response(
                {"error": "Password required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        mail = imaplib.IMAP4_SSL(
            email_account.imap_server,
            email_account.imap_port
        )
        mail.login(email_account.email_address, password)
        mail.select('"[Gmail]/All Mail"')

        for message in messages:
            try:
                uid = message.external_message_id.split("_")[-1]

                # Move to Trash
                mail.uid("STORE", uid, "+X-GM-LABELS", "(\\Trash)")
                mail.uid("STORE", uid, "-X-GM-LABELS", "(\\Inbox)")

                # Update DB
                message.folder = "trash"
                message.save()

            except Exception:
                continue

        mail.logout()

        return Response(
            {"status": "conversation_deleted"},
            status=status.HTTP_200_OK
        )

class ToggleConversationStarAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):

        try:
            conversation = Conversation.objects.get(
                id=conversation_id,
                user=request.user
            )
        except Conversation.DoesNotExist:
            return Response(
                {"error": "Conversation not found"},
                status=404
            )

        conversation.is_starred = not conversation.is_starred
        conversation.save()

        return Response({
            "status": "success",
            "is_starred": conversation.is_starred
        })
