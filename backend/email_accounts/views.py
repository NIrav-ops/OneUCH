
from django.utils import timezone

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

from accounts.authentication import (
    get_active_membership,
)

from email_accounts.services.credential_vault import (
    CredentialVaultError,
)

from .models import (
    EmailAccount,
)

from inbox.models import (
    InboxMessage,
)

from inbox.tasks import (
    send_email_task,
)


class SendEmailAPIView(
    APIView
):
    permission_classes = [
        IsAuthenticated
    ]

    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        membership = (
            get_active_membership(
                request.user
            )
        )

        if membership is None:
            return Response(
                {
                    "error":
                        "Active workspace required."
                },
                status=(
                    status.HTTP_403_FORBIDDEN
                ),
            )

        organization = (
            membership.organization
        )

        email_account = (
            EmailAccount.objects
            .filter(
                user=request.user,
                organization=organization,
                account_type="imap",
                is_active=True,
            )
            .order_by(
                "-id"
            )
            .first()
        )

        if email_account is None:
            return Response(
                {
                    "error":
                        "No active Other Work Email mailbox."
                },
                status=(
                    status.HTTP_400_BAD_REQUEST
                ),
            )

        if not (
            email_account
            .is_credential_valid()
        ):
            return Response(
                {
                    "error":
                        "Mailbox credential requires re-authentication."
                },
                status=(
                    status.HTTP_400_BAD_REQUEST
                ),
            )

        try:
            credential = (
                email_account
                .get_credential()
            )

        except CredentialVaultError:
            credential = None

        if not credential:
            return Response(
                {
                    "error":
                        "Mailbox credential is unavailable."
                },
                status=(
                    status.HTTP_400_BAD_REQUEST
                ),
            )

        to_email = (
            request.data.get(
                "to"
            )
        )

        subject = (
            request.data.get(
                "subject",
                "",
            )
        )

        body = (
            request.data.get(
                "body",
                "",
            )
        )

        if not to_email:
            return Response(
                {
                    "error":
                        "Recipient email is required"
                },
                status=(
                    status.HTTP_400_BAD_REQUEST
                ),
            )

        inbox_message = (
            InboxMessage.objects.create(
                user=request.user,
                organization=organization,
                email_account=email_account,
                platform="imap",
                direction="outbound",
                external_message_id="pending",
                sender=(
                    email_account.email_address
                ),
                recipients=to_email,
                subject=subject,
                body=body,
                received_at=timezone.now(),
                is_read=True,
                status="queued",
            )
        )

        send_email_task.delay(
            email_account.id,
            to_email,
            subject,
            body,
            inbox_message.id,
        )

        return Response(
            {
                "status":
                    "Email queued for sending"
            },
            status=(
                status.HTTP_202_ACCEPTED
            ),
        )


class EmailAccountListAPIView(
    APIView
):
    permission_classes = [
        IsAuthenticated
    ]

    def get(
        self,
        request,
    ):
        membership = (
            get_active_membership(
                request.user
            )
        )

        if membership is None:
            return Response(
                [],
                status=(
                    status.HTTP_403_FORBIDDEN
                ),
            )

        accounts = (
            EmailAccount.objects
            .filter(
                user=request.user,
                organization=(
                    membership.organization
                ),
            )
            .order_by(
                "id"
            )
        )

        return Response(
            [
                {
                    "id":
                        account.id,

                    "email_address":
                        account.email_address,

                    "account_type":
                        account.account_type,
                }

                for account
                in accounts
            ]
        )
