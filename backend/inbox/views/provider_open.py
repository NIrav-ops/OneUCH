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

from platform_core.api.tenant import (
    get_user_organization_or_404,
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
