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
    set_message_read,
)


class MessageReadStateAPIView(
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
        is_read = (
            request.data.get(
                "is_read"
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


        message = (
            InboxMessage.objects
            .select_related(
                "email_account",
                "conversation",
            )
            .filter(
                id=message_id,
                user=request.user,
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


        try:

            set_message_read(
                message=message,
                user=request.user,
                is_read=is_read,
            )

        except MailMutationError as exc:

            return Response(
                {
                    "error":
                        str(exc)
                },
                status=502,
            )


        return Response(
            {
                "status":
                    (
                        "read"
                        if is_read
                        else "unread"
                    ),

                "is_read":
                    is_read,
            }
        )
