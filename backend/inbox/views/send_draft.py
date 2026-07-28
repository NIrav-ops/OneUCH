from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from inbox.models import InboxMessage
from inbox.views.send_message import UnifiedSendMessageAPIView


class SendDraftAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, draft_id):

        try:
            draft = InboxMessage.objects.get(
                id=draft_id,
                user=request.user,
                is_draft=True
            )

            data = {
                "to": draft.recipients,
                "subject": draft.subject,
                "body": draft.body,
                "conversation_id": draft.conversation.id if draft.conversation else None,
                "account_id": draft.email_account.id if draft.email_account else None,
            }

            # 🔥 CALL SEND API
            send_api = UnifiedSendMessageAPIView()
            response = send_api.post(request._request)

            # DELETE draft after sending
            draft.delete()

            return Response({"status": "draft_sent"})

        except Exception as e:
            return Response({"error": str(e)}, status=500)