from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from inbox.models import (
    InboxMessage,
)

from inbox.views.send_message import (
    UnifiedSendMessageAPIView,
)


class SendDraftAPIView(
    APIView
):
    permission_classes = [
        IsAuthenticated
    ]


    def post(
        self,
        request,
        draft_id,
    ):

        try:

            draft = (
                InboxMessage.objects
                .select_related(
                    "conversation",
                    "email_account",
                )
                .get(
                    id=draft_id,
                    user=request.user,
                    is_draft=True,
                )
            )

        except InboxMessage.DoesNotExist:

            return Response(
                {
                    "error":
                        "Draft not found"
                },
                status=(
                    status
                    .HTTP_404_NOT_FOUND
                ),
            )


        recipient_meta = (
            draft.recipient_meta
            if isinstance(
                draft.recipient_meta,
                dict,
            )
            else {}
        )


        has_structured = any(
            recipient_meta.get(
                bucket
            )
            for bucket in (
                "to",
                "cc",
                "bcc",
            )
        )


        if has_structured:

            to_value = (
                recipient_meta.get(
                    "to",
                    [],
                )
            )

            cc_value = (
                recipient_meta.get(
                    "cc",
                    [],
                )
            )

            bcc_value = (
                recipient_meta.get(
                    "bcc",
                    [],
                )
            )

        else:

            # Legacy pre-P2 draft compatibility.
            to_value = (
                draft.recipients
            )

            cc_value = []

            bcc_value = []


        data = {
            "to":
                to_value,

            "cc":
                cc_value,

            "bcc":
                bcc_value,

            "subject":
                draft.subject,

            "body":
                draft.body,

            "conversation_id":
                (
                    draft.conversation.id
                    if draft.conversation
                    else None
                ),

            "account_id":
                (
                    draft.email_account.id
                    if draft.email_account
                    else None
                ),
        }


        send_api = (
            UnifiedSendMessageAPIView()
        )


        response = (
            send_api.send_with_data(
                request=request,
                data=data,
            )
        )


        if not (
            200
            <=
            response.status_code
            <
            300
        ):
            return response


        sent_message_id = (
            response.data.get(
                "message_id"
            )
            if hasattr(
                response,
                "data",
            )
            else None
        )


        conversation_id = (
            response.data.get(
                "conversation_id"
            )
            if hasattr(
                response,
                "data",
            )
            else None
        )


        draft.delete()


        return Response(
            {
                "status":
                    "draft_sent",

                "message_id":
                    sent_message_id,

                "conversation_id":
                    conversation_id,
            },
            status=(
                status
                .HTTP_200_OK
            ),
        )
