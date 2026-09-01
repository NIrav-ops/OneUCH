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

from inbox.services.provider_links import (
    ProviderLinkError,
    provider_open_url,
)


class ProviderOpenAPIView(
    APIView
):
    permission_classes = [
        IsAuthenticated
    ]


    def get(
        self,
        request,
        message_id,
    ):
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

            url = (
                provider_open_url(
                    message
                )
            )

        except ProviderLinkError as exc:

            return Response(
                {
                    "error":
                        str(exc)
                },
                status=409,
            )


        return Response(
            {
                "provider":
                    (
                        message.email_account
                        .account_type
                    ),

                "url":
                    url,
            }
        )
