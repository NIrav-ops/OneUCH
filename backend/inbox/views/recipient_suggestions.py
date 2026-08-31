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

from inbox.services.recipient_directory import (
    RecipientDirectoryUnavailable,
    suggest_recipients,
)


class RecipientSuggestionAPIView(
    APIView
):
    permission_classes = [
        IsAuthenticated
    ]


    def get(
        self,
        request,
    ):
        query = (
            request.query_params
            .get(
                "q",
                "",
            )
        )

        limit = (
            request.query_params
            .get(
                "limit",
                10,
            )
        )


        try:
            result = (
                suggest_recipients(
                    user=request.user,
                    query=query,
                    limit=limit,
                    refresh=True,
                )
            )

        except RecipientDirectoryUnavailable as exc:
            return Response(
                {
                    "error":
                        str(exc)
                },
                status=(
                    status
                    .HTTP_400_BAD_REQUEST
                ),
            )


        return Response(
            result,
            status=(
                status
                .HTTP_200_OK
            ),
        )
