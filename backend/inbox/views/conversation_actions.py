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
    Conversation,
)

from inbox.services.mail_mutations import (
    MailMutationError,
    refresh_conversation_local_state,
    set_conversation_read,
    set_conversation_star,
    trash_conversation,
)


def _conversation(
    *,
    user,
    conversation_id,
):
    return (
        Conversation.objects
        .select_related(
            "email_account"
        )
        .filter(
            id=conversation_id,
            user=user,
        )
        .first()
    )


class MarkConversationReadAPIView(
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
        conversation = (
            _conversation(
                user=request.user,
                conversation_id=(
                    conversation_id
                ),
            )
        )


        if conversation is None:

            return Response(
                {
                    "error":
                        "Conversation not found"
                },
                status=404,
            )


        is_read = (
            request.data.get(
                "is_read",
                True,
            )
        )


        if not isinstance(
            is_read,
            bool,
        ):

            return Response(
                {
                    "error":
                        "is_read must be boolean"
                },
                status=400,
            )


        account = (
            conversation.email_account
        )


        if (
            account
            and
            account.account_type in {
                "gmail",
                "outlook",
            }
        ):

            try:

                result = (
                    set_conversation_read(
                        conversation=(
                            conversation
                        ),
                        user=request.user,
                        is_read=is_read,
                    )
                )

            except MailMutationError as exc:

                return Response(
                    {
                        "error":
                            str(exc)
                    },
                    status=502,
                )


            if result[
                "errors"
            ]:

                return Response(
                    {
                        "status":
                            "partial",

                        "updated":
                            result[
                                "updated"
                            ],

                        "errors":
                            result[
                                "errors"
                            ],
                    },
                    status=502,
                )


        else:

            updated = (
                conversation.messages
                .filter(
                    user=request.user,
                    is_draft=False,
                )
                .exclude(
                    folder="trash"
                )
                .update(
                    is_read=is_read
                )
            )


            refresh_conversation_local_state(
                conversation
            )


            result = {
                "updated":
                    updated,

                "errors":
                    [],
            }


        return Response(
            {
                "status":
                    (
                        "conversation marked as read"
                        if is_read
                        else "conversation marked as unread"
                    ),

                "is_read":
                    is_read,

                "updated":
                    result[
                        "updated"
                    ],
            }
        )


class ToggleConversationStarAPIView(
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
        conversation = (
            _conversation(
                user=request.user,
                conversation_id=(
                    conversation_id
                ),
            )
        )


        if conversation is None:

            return Response(
                {
                    "error":
                        "Conversation not found"
                },
                status=404,
            )


        new_state = (
            not conversation.is_starred
        )


        account = (
            conversation.email_account
        )


        if (
            account
            and
            account.account_type in {
                "gmail",
                "outlook",
            }
        ):

            try:

                result = (
                    set_conversation_star(
                        conversation=(
                            conversation
                        ),
                        user=request.user,
                        is_starred=(
                            new_state
                        ),
                    )
                )

            except MailMutationError as exc:

                return Response(
                    {
                        "error":
                            str(exc)
                    },
                    status=502,
                )


            if result[
                "errors"
            ]:

                return Response(
                    {
                        "status":
                            "partial",

                        "updated":
                            result[
                                "updated"
                            ],

                        "errors":
                            result[
                                "errors"
                            ],
                    },
                    status=502,
                )


        else:

            conversation.messages.filter(
                user=request.user,
                is_draft=False,
            ).exclude(
                folder="trash"
            ).update(
                is_starred=new_state
            )


            refresh_conversation_local_state(
                conversation
            )


        conversation.refresh_from_db()


        return Response(
            {
                "status":
                    "success",

                "is_starred":
                    conversation.is_starred,
            }
        )


class DeleteConversationAPIView(
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
        conversation = (
            _conversation(
                user=request.user,
                conversation_id=(
                    conversation_id
                ),
            )
        )


        if conversation is None:

            return Response(
                {
                    "error":
                        "Conversation not found"
                },
                status=404,
            )


        account = (
            conversation.email_account
        )


        if (
            account
            and
            account.account_type in {
                "gmail",
                "outlook",
            }
        ):

            try:

                result = (
                    trash_conversation(
                        conversation=(
                            conversation
                        ),
                        user=request.user,
                    )
                )

            except MailMutationError as exc:

                return Response(
                    {
                        "error":
                            str(exc)
                    },
                    status=502,
                )


            if result[
                "errors"
            ]:

                return Response(
                    {
                        "status":
                            "partial",

                        "updated":
                            result[
                                "updated"
                            ],

                        "errors":
                            result[
                                "errors"
                            ],
                    },
                    status=502,
                )


        elif (
            account
            and
            account.account_type
            ==
            "imap"
        ):

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


                for message in (
                    conversation.messages
                    .filter(
                        user=request.user,
                        is_draft=False,
                    )
                    .exclude(
                        folder="trash"
                    )
                ):

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


                    message.folder = (
                        "trash"
                    )

                    message.save(
                        update_fields=[
                            "folder"
                        ]
                    )

            finally:

                try:
                    mail.logout()
                except Exception:
                    pass


            refresh_conversation_local_state(
                conversation
            )


        else:

            return Response(
                {
                    "error":
                        "No supported mailbox linked"
                },
                status=400,
            )


        return Response(
            {
                "status":
                    "conversation_deleted"
            }
        )
