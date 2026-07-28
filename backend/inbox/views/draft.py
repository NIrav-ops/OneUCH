from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

from email_accounts.models import EmailAccount
from inbox.models import InboxMessage, Conversation


class DraftSaveAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        conversation_id = request.data.get("conversation_id")
        subject = request.data.get("subject", "")
        body = request.data.get("body", "")
        recipients = request.data.get("recipients", "")
        email_account_id = (
            request.data.get("email_account_id")
            or request.data.get("account_id")
        )

        email_account = None
        if email_account_id:
            email_account = EmailAccount.objects.filter(
                id=email_account_id,
                user=request.user
            ).first()
            if not email_account:
                return Response(
                    {"error": "Email account not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            email_account = EmailAccount.objects.filter(
                user=request.user
            ).first()

        if not conversation_id:
            # 🔥 AUTO CREATE CONVERSATION (ENTERPRISE FIX)
            conversation = Conversation.objects.create(
                user=request.user,
                organization=request.user.organization_membership.organization,
                subject=subject or "Draft",
                conversation_key=f"draft_{request.user.id}_{timezone.now().timestamp()}",
                email_account=email_account
            )
        else:
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

        draft, created = InboxMessage.objects.update_or_create(
            user=request.user,
            conversation=conversation,
            is_draft=True,
            defaults={
                "organization": request.user.organization_membership.organization,
                "platform": email_account.account_type if email_account else "gmail",
                "direction": "outbound",
                "email_account": email_account,
                "sender": request.user.email,
                "recipients": recipients,
                "subject": subject,
                "body": body,
                "received_at": timezone.now(),
                "folder": "draft",
                "is_draft": True,              
                "status": "queued",  
                "external_message_id": f"draft-{conversation.id}",
            },
        )

        conversation.last_message = draft
        conversation.last_message_at = draft.received_at
        conversation.last_message_preview = draft.body[:120] if draft.body else ""
        conversation.save()

        return Response(
            {
                "status": "draft_saved",
                "draft_id": draft.id,
                "conversation_id": conversation.id,
            },
            status=status.HTTP_200_OK,
        )

class DraftListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        drafts = InboxMessage.objects.filter(
            user=request.user,
            is_draft=True
        ).select_related("conversation").order_by("-received_at")

        data = [
            {
                "id": d.id,
                "conversation_id": d.conversation.id if d.conversation else None,
                "subject": d.subject,
                "recipients": d.recipients,
                "updated_at": d.received_at,
            }
            for d in drafts
        ]

        return Response(data)
