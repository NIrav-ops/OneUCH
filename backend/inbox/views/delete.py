import imaplib

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
    InboxMessage,
)

from inbox.services.mail_mutations import (
    MailMutationError,
    refresh_conversation_local_state,
    trash_message,
)

from platform_core.api.tenant import (
    get_user_organization_or_404,
)


class DeleteMessageAPIView(
    APIView
):
    permission_classes = [
        IsAuthenticated
    ]


    def post(
        self,
        request,
        message_id,
    ):
        organization = (
            get_user_organization_or_404(
                request
            )
        )

        message = (
            InboxMessage.objects
            .select_related(
                "email_account",
                "conversation",
            )
            .filter(
                id=message_id,
                user=request.user,
                organization=organization,
            )
            .first()
        )


        if message is None:

            return Response(
                {
                    "error":
                        "Message not found"
                },
                status=404,
            )


        account = (
            message.email_account
        )


        if account is None:

            return Response(
                {
                    "error":
                        "Message has no connected mailbox"
                },
                status=400,
            )


        if account.account_type in {
            "gmail",
            "outlook",
        }:

            try:

                trash_message(
                    message=message,
                    user=request.user,
                )

            except MailMutationError as exc:

                return Response(
                    {
                        "error":
                            str(exc)
                    },
                    status=502,
                )


        elif account.account_type == "imap":

            if (
                account.user_id
                !=
                request.user.id
                or
                not account.is_active
            ):

                return Response(
                    {
                        "error":
                            "Invalid IMAP mailbox"
                    },
                    status=400,
                )


            password = (
                request.data.get(
                    "password"
                )
            )


            if not password:

                return Response(
                    {
                        "error":
                            "Password required"
                    },
                    status=400,
                )


            mail = (
                imaplib.IMAP4_SSL(
                    account.imap_server,
                    account.imap_port,
                )
            )


            try:

                mail.login(
                    account.email_address,
                    password,
                )

                mail.select(
                    '"[Gmail]/All Mail"'
                )


                uid = (
                    message
                    .external_message_id
                    .split(
                        "_"
                    )[
                        -1
                    ]
                )


                mail.uid(
                    "STORE",
                    uid,
                    "+X-GM-LABELS",
                    "(\\Trash)",
                )

                mail.uid(
                    "STORE",
                    uid,
                    "-X-GM-LABELS",
                    "(\\Inbox)",
                )

            finally:

                try:
                    mail.logout()
                except Exception:
                    pass


            message.folder = (
                "trash"
            )

            message.save(
                update_fields=[
                    "folder"
                ]
            )


            refresh_conversation_local_state(
                message.conversation
            )


        else:

            return Response(
                {
                    "error":
                        "Unsupported mailbox provider"
                },
                status=400,
            )


        return Response(
            {
                "status":
                    "deleted"
            }
        )
