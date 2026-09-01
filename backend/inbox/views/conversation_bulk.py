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
    set_conversation_read,
    set_conversation_star,
)


def _conversation_ids(
    request,
):
    value = (
        request.data.get(
            "conversation_ids",
            [],
        )
    )


    if not isinstance(
        value,
        list,
    ):
        return None


    try:

        return [
            int(
                item
            )
            for item
            in value
        ]

    except (
        TypeError,
        ValueError,
    ):

        return None


class BulkMarkConversationReadAPIView(
    APIView
):
    permission_classes = [
        IsAuthenticated
    ]


    def post(
        self,
        request,
    ):
        conversation_ids = (
            _conversation_ids(
                request
            )
        )


        if not conversation_ids:

            return Response(
                {
                    "error":
                        "No valid conversation_ids provided"
                },
                status=400,
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


        conversations = (
            Conversation.objects
            .filter(
                id__in=(
                    conversation_ids
                ),
                user=request.user,
            )
            .select_related(
                "email_account"
            )
        )


        results = []

        errors = []


        for conversation in conversations:

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


                if result[
                    "errors"
                ]:

                    errors.append(
                        {
                            "conversation_id":
                                conversation.id,

                            "error":
                                "One or more provider "
                                "messages failed.",
                        }
                    )


                else:

                    results.append(
                        {
                            "conversation_id":
                                conversation.id,

                            "status":
                                (
                                    "read"
                                    if is_read
                                    else "unread"
                                ),
                        }
                    )


            except MailMutationError as exc:

                errors.append(
                    {
                        "conversation_id":
                            conversation.id,

                        "error":
                            str(exc),
                    }
                )


        return Response(
            {
                "updated":
                    results,

                "errors":
                    errors,
            }
        )


class BulkToggleConversationStarAPIView(
    APIView
):
    permission_classes = [
        IsAuthenticated
    ]


    def post(
        self,
        request,
    ):
        conversation_ids = (
            _conversation_ids(
                request
            )
        )


        if not conversation_ids:

            return Response(
                {
                    "error":
                        "No valid conversation_ids provided"
                },
                status=400,
            )


        explicit_state = (
            request.data.get(
                "is_starred",
                None,
            )
        )


        if (
            explicit_state is not None
            and
            not isinstance(
                explicit_state,
                bool,
            )
        ):

            return Response(
                {
                    "error":
                        "is_starred must be boolean"
                },
                status=400,
            )


        conversations = (
            Conversation.objects
            .filter(
                id__in=(
                    conversation_ids
                ),
                user=request.user,
            )
            .select_related(
                "email_account"
            )
        )


        results = []

        errors = []


        for conversation in conversations:

            target_state = (
                explicit_state
                if explicit_state is not None
                else
                not conversation.is_starred
            )


            try:

                result = (
                    set_conversation_star(
                        conversation=(
                            conversation
                        ),
                        user=request.user,
                        is_starred=(
                            target_state
                        ),
                    )
                )


                if result[
                    "errors"
                ]:

                    errors.append(
                        {
                            "conversation_id":
                                conversation.id,

                            "error":
                                "One or more provider "
                                "messages failed.",
                        }
                    )


                else:

                    results.append(
                        {
                            "conversation_id":
                                conversation.id,

                            "status":
                                (
                                    "starred"
                                    if target_state
                                    else "unstarred"
                                ),

                            "is_starred":
                                target_state,
                        }
                    )


            except MailMutationError as exc:

                errors.append(
                    {
                        "conversation_id":
                            conversation.id,

                        "error":
                            str(exc),
                    }
                )


        return Response(
            {
                "updated":
                    results,

                "errors":
                    errors,
            }
        )
