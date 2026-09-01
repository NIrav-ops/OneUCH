from rest_framework import status

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

from inbox.models import (
    OrganizationUser,
)


MAX_SIGNATURE_LENGTH = 10000


def _payload(
    account,
):
    signature_text = (
        account.signature_text
        or ""
    )

    return {
        "account_id":
            account.id,

        "account_type":
            account.account_type,

        "email_address":
            account.email_address,

        "signature_enabled":
            account.signature_enabled,

        "signature_text":
            signature_text,

        "signature_configured":
            bool(
                account.signature_enabled
                and
                signature_text.strip()
            ),
    }


class MailboxSignatureAPIView(
    APIView
):
    permission_classes = [
        IsAuthenticated
    ]


    def _account(
        self,
        *,
        request,
        account_id,
    ):
        membership = (
            OrganizationUser.objects
            .filter(
                user=request.user,
                organization__is_active=True,
            )
            .first()
        )


        if membership is None:
            return None, Response(
                {
                    "detail":
                        "Active organization membership required."
                },
                status=(
                    status.HTTP_403_FORBIDDEN
                ),
            )


        account = (
            EmailAccount.objects
            .filter(
                id=account_id,
                user=request.user,
                is_active=True,
                account_type__in=[
                    "gmail",
                    "outlook",
                ],
            )
            .first()
        )


        if account is None:
            return None, Response(
                {
                    "detail":
                        "Mailbox not found."
                },
                status=(
                    status.HTTP_404_NOT_FOUND
                ),
            )


        return account, None


    def get(
        self,
        request,
        account_id,
    ):
        account, error = (
            self._account(
                request=request,
                account_id=account_id,
            )
        )


        if error is not None:
            return error


        return Response(
            _payload(
                account
            )
        )


    def patch(
        self,
        request,
        account_id,
    ):
        account, error = (
            self._account(
                request=request,
                account_id=account_id,
            )
        )


        if error is not None:
            return error


        signature_text = (
            request.data.get(
                "signature_text",
                account.signature_text,
            )
        )


        if signature_text is None:
            signature_text = ""


        signature_text = str(
            signature_text
        )


        if (
            len(
                signature_text
            )
            >
            MAX_SIGNATURE_LENGTH
        ):
            return Response(
                {
                    "detail":
                        "Signature is too long."
                },
                status=(
                    status.HTTP_400_BAD_REQUEST
                ),
            )


        signature_enabled = (
            request.data.get(
                "signature_enabled",
                account.signature_enabled,
            )
        )


        if not isinstance(
            signature_enabled,
            bool,
        ):
            return Response(
                {
                    "detail":
                        "signature_enabled must be a boolean."
                },
                status=(
                    status.HTTP_400_BAD_REQUEST
                ),
            )


        signature_text = (
            signature_text.rstrip()
        )


        if (
            signature_enabled
            and
            not signature_text.strip()
        ):
            return Response(
                {
                    "detail":
                        "Add a signature before enabling it."
                },
                status=(
                    status.HTTP_400_BAD_REQUEST
                ),
            )


        account.signature_text = (
            signature_text
        )

        account.signature_enabled = (
            signature_enabled
        )


        account.save(
            update_fields=[
                "signature_text",
                "signature_enabled",
            ]
        )


        return Response(
            _payload(
                account
            )
        )
