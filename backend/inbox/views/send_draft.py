from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from inbox.models import (
    InboxMessage,
)

from inbox.services.persistent_outbound_attachments import (
    load_persisted_outbound_attachments,
    move_persisted_outbound_attachments,
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
                .prefetch_related(
                    "attachments"
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


        try:

            prepared_attachments = (
                load_persisted_outbound_attachments(
                    message=draft
                )
            )

        except ValueError as exc:

            return Response(
                {
                    "error":
                        str(exc)
                },
                status=400,
            )


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
                prepared_attachments=(
                    prepared_attachments
                ),
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


        attachment_count = len(
            prepared_attachments
        )


        if attachment_count:

            sent_message = (
                InboxMessage.objects
                .filter(
                    id=sent_message_id,
                    user=request.user,
                    is_draft=False,
                )
                .first()
            )


            if sent_message is None:

                return Response(
                    {
                        "error": (
                            "Draft was sent but the local Sent "
                            "message could not be resolved for "
                            "attachment transfer."
                        )
                    },
                    status=500,
                )


            move_persisted_outbound_attachments(
                source_message=draft,
                target_message=sent_message,
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

                "attachment_count":
                    attachment_count,
            },
            status=(
                status
                .HTTP_200_OK
            ),
        )
