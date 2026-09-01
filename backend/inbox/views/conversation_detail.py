from rest_framework.permissions import (
    IsAuthenticated,
)

from rest_framework.response import (
    Response,
)

from rest_framework.views import (
    APIView,
)

from inbox.models import (
    Conversation,
    InboxMessage,
)


class ConversationDetailAPIView(
    APIView
):
    permission_classes = [
        IsAuthenticated
    ]


    def get(
        self,
        request,
        conversation_id,
    ):
        user = (
            request.user
        )


        conversation = (
            Conversation.objects
            .filter(
                id=conversation_id,
                user=user,
            )
            .first()
        )


        if conversation is None:

            return Response(
                {
                    "messages":
                        [],

                    "attachments":
                        [],
                }
            )


        messages = (
            InboxMessage.objects
            .filter(
                user=user,
                conversation=(
                    conversation
                ),
            )
            .order_by(
                "received_at",
                "id",
            )
        )


        all_attachments = []


        for message in messages:

            for attachment in (
                message.attachment_meta
                or []
            ):

                all_attachments.append(
                    {
                        "message_id":
                            message.id,

                        "filename":
                            attachment.get(
                                "filename"
                            ),

                        "attachment_id":
                            attachment.get(
                                "attachment_id"
                            ),

                        "mime_type":
                            attachment.get(
                                "mime_type"
                            ),

                        "downloadable":
                            bool(
                                attachment.get(
                                    "attachment_id"
                                )
                            ),
                    }
                )


        return Response(
            {
                "messages": [
                    {
                        "id":
                            message.id,

                        "sender":
                            message.sender,

                        "sender_meta":
                            message.sender_meta,

                        "recipients":
                            message.recipients,

                        "recipient_meta":
                            message.recipient_meta,

                        "direction":
                            message.direction,

                        "platform":
                            message.platform,

                        "email_account_id":
                            message.email_account_id,

                        "subject":
                            (
                                message.subject
                                or
                                "No Subject"
                            ),

                        "body":
                            (
                                message.body
                                or
                                ""
                            ),

                        "time":
                            message.received_at,

                        "is_read":
                            message.is_read,

                        "is_starred":
                            message.is_starred,

                        "status":
                            message.status,

                        "in_reply_to":
                            message.in_reply_to,

                        "external_message_id":
                            message.external_message_id,

                        "external_conversation_id":
                            message.external_conversation_id,
                    }

                    for message
                    in messages
                ],

                "attachments":
                    all_attachments,
            }
        )
