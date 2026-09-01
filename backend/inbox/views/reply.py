from django.utils import (
    timezone,
)

from rest_framework import (
    status,
)

from rest_framework.permissions import (
    IsAuthenticated,
)

from rest_framework.response import (
    Response,
)

from rest_framework.views import (
    APIView,
)

from email_accounts.models import (
    EmailAccount,
)

from email_accounts.services.signatures import (
    apply_account_signature,
)

from inbox.models import (
    Conversation,
    InboxMessage,
)

from inbox.services.reply_recipients import (
    ReplyRecipientError,
    resolve_reply_recipients,
)

from inbox.tasks import (
    send_email_task,
)


class ReplyConversationAPIView(
    APIView
):
    permission_classes = [
        IsAuthenticated
    ]


    def post(
        self,
        request,
        conversation_id,
    ):
        body = (
            request.data.get(
                "body"
            )
        )


        if not body:

            return Response(
                {
                    "error":
                        "Reply body is required"
                },
                status=(
                    status
                    .HTTP_400_BAD_REQUEST
                ),
            )


        mode = (
            request.data.get(
                "mode",
                "reply",
            )
        )


        if mode not in {
            "reply",
            "reply_all",
        }:

            return Response(
                {
                    "error":
                        "Unsupported reply mode"
                },
                status=400,
            )


        conversation = (
            Conversation.objects
            .select_related(
                "email_account"
            )
            .filter(
                id=conversation_id,
                user=request.user,
            )
            .first()
        )


        if conversation is None:

            return Response(
                {
                    "error":
                        "Conversation not found"
                },
                status=(
                    status
                    .HTTP_404_NOT_FOUND
                ),
            )


        latest_message = (
            conversation.messages
            .select_related(
                "email_account"
            )
            .filter(
                user=request.user,
                is_draft=False,
            )
            .exclude(
                folder="trash"
            )
            .order_by(
                "-received_at",
                "-id",
            )
            .first()
        )


        if latest_message is None:

            return Response(
                {
                    "error":
                        "No messages in conversation"
                },
                status=(
                    status
                    .HTTP_400_BAD_REQUEST
                ),
            )


        source_account = (
            latest_message.email_account
            or
            conversation.email_account
        )


        override_account_id = (
            request.data.get(
                "email_account_id"
            )
        )


        if override_account_id:

            email_account = (
                EmailAccount.objects
                .filter(
                    id=override_account_id,
                    user=request.user,
                    is_active=True,
                )
                .first()
            )


            if email_account is None:

                return Response(
                    {
                        "error":
                            "No valid email account found"
                    },
                    status=400,
                )


            if (
                source_account
                and
                email_account.id
                !=
                source_account.id
            ):

                return Response(
                    {
                        "error":
                            "Replies must use the original mailbox"
                    },
                    status=400,
                )


        else:

            email_account = (
                source_account
            )


        if (
            email_account is None
            or
            email_account.user_id
            !=
            request.user.id
            or
            not email_account.is_active
        ):

            return Response(
                {
                    "error":
                        "No valid email account found"
                },
                status=(
                    status
                    .HTTP_400_BAD_REQUEST
                ),
            )


        try:

            (
                recipient_meta,
                recipients_flat,
            ) = (
                resolve_reply_recipients(
                    message=(
                        latest_message
                    ),
                    user=request.user,
                    mode=mode,
                )
            )

        except ReplyRecipientError as exc:

            return Response(
                {
                    "error":
                        str(exc)
                },
                status=400,
            )


        body = (
            apply_account_signature(
                account=email_account,
                body=body,
            )
        )


        subject = (
            latest_message.subject
            or
            conversation.subject
            or
            "No Subject"
        )


        if not subject.lower().startswith(
            "re:"
        ):

            subject = (
                "Re: "
                +
                subject
            )


        sender_email = (
            str(
                email_account.email_address
            )
            .strip()
            .lower()
        )


        sender_meta = {
            "name":
                "",

            "email":
                sender_email,
        }


        reply_message = (
            InboxMessage.objects
            .create(
                user=request.user,
                organization=(
                    request.user
                    .organization_membership
                    .organization
                ),
                platform=(
                    email_account
                    .account_type
                ),
                email_account=(
                    email_account
                ),
                direction="outbound",
                folder="outbox",
                external_message_id=(
                    "pending"
                ),
                external_conversation_id=(
                    latest_message
                    .external_conversation_id
                    or
                    conversation
                    .external_conversation_id
                ),
                conversation=(
                    conversation
                ),
                in_reply_to=(
                    latest_message
                    .external_message_id
                ),
                sender=(
                    sender_email
                ),
                sender_meta=(
                    sender_meta
                ),
                recipients=(
                    recipients_flat
                ),
                recipient_meta=(
                    recipient_meta
                ),
                subject=subject,
                body=body,
                received_at=(
                    timezone.now()
                ),
                is_read=True,
                is_draft=False,
                status="queued",
            )
        )


        primary_to = (
            ", ".join(
                item[
                    "email"
                ]
                for item
                in recipient_meta[
                    "to"
                ]
            )
        )


        task_args = [
            email_account.id,
            primary_to,
            subject,
            body,
            reply_message.id,
        ]


        if mode == "reply_all":

            task_args.append(
                "reply_all"
            )


        send_email_task.delay(
            *task_args
        )


        return Response(
            {
                "status":
                    "Reply queued successfully",

                "mode":
                    mode,

                "message_id":
                    reply_message.id,
            },
            status=(
                status
                .HTTP_202_ACCEPTED
            ),
        )
