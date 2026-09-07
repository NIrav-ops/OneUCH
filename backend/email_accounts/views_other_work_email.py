from django.db import (
    IntegrityError,
    transaction,
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

from accounts.authentication import (
    get_active_membership,
)

from email_accounts.models import (
    EmailAccount,
)

from email_accounts.serializers import (
    OtherWorkEmailSetupSerializer,
)


class OtherWorkEmailSetupAPIView(
    APIView
):
    permission_classes = [
        IsAuthenticated
    ]

    def post(
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
                {
                    "error":
                        "Active workspace required."
                },
                status=(
                    status.HTTP_403_FORBIDDEN
                ),
            )

        serializer = (
            OtherWorkEmailSetupSerializer(
                data=request.data
            )
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=(
                    status.HTTP_400_BAD_REQUEST
                ),
            )

        data = (
            serializer.validated_data
        )

        organization = (
            membership.organization
        )

        try:
            with transaction.atomic():

                existing = (
                    EmailAccount.objects
                    .select_for_update()
                    .filter(
                        organization=organization,
                        account_type="imap",
                        email_address=(
                            data[
                                "email_address"
                            ]
                        ),
                    )
                    .first()
                )

                if (
                    existing is not None
                    and
                    existing.user_id
                    !=
                    request.user.id
                ):
                    return Response(
                        {
                            "error": (
                                "Mailbox already belongs "
                                "to this workspace."
                            )
                        },
                        status=(
                            status.HTTP_409_CONFLICT
                        ),
                    )

                created = (
                    existing is None
                )

                if created:
                    account = (
                        EmailAccount(
                            user=request.user,
                            organization=organization,
                            account_type="imap",
                            email_address=(
                                data[
                                    "email_address"
                                ]
                            ),
                        )
                    )

                else:
                    account = existing

                account.imap_server = (
                    data[
                        "imap_server"
                    ]
                )

                account.imap_port = (
                    data[
                        "imap_port"
                    ]
                )

                account.smtp_server = (
                    data[
                        "smtp_server"
                    ]
                )

                account.smtp_port = (
                    data[
                        "smtp_port"
                    ]
                )

                account.set_credential(
                    data[
                        "credential"
                    ]
                )

                account.credential_status = (
                    "active"
                )

                account.credential_expires_at = (
                    None
                )

                account.last_verified_at = (
                    None
                )

                account.is_active = (
                    True
                )

                # Connection parameters changed or were newly
                # created. Do not reuse an IMAP UID cursor from
                # a previous server configuration.
                account.last_synced_uids = {}

                account.history_sync_completed_at = (
                    None
                )

                account.save()

        except IntegrityError:
            return Response(
                {
                    "error": (
                        "Mailbox configuration conflicts "
                        "with an existing workspace mailbox."
                    )
                },
                status=(
                    status.HTTP_409_CONFLICT
                ),
            )

        return Response(
            {
                "id":
                    account.id,

                "email_address":
                    account.email_address,

                "account_type":
                    "imap",

                "credential_status":
                    account.credential_status,

                "is_active":
                    account.is_active,

                "provider_label":
                    "Other Work Email",

                # last_verified_at remains empty until actual
                # provider validation/synchronization occurs.
                "provider_verified":
                    bool(
                        account.last_verified_at
                    ),
            },
            status=(
                status.HTTP_201_CREATED
                if created
                else
                status.HTTP_200_OK
            ),
        )

class OtherWorkEmailSyncAPIView(
    APIView
):
    """
    Queue the already-governed single-mailbox synchronization
    task for one explicitly owned Other Work Email account.

    No IMAP/SMTP provider work executes in this HTTP request.
    """

    permission_classes = [
        IsAuthenticated
    ]

    def post(
        self,
        request,
        account_id,
    ):
        membership = (
            get_active_membership(
                request.user
            )
        )

        if membership is None:
            return Response(
                {
                    "status":
                        "workspace_required",

                    "error":
                        "Active workspace required.",
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
                organization=(
                    membership.organization
                ),
                account_type="imap",
                is_active=True,
            )
            .first()
        )

        if account is None:
            return Response(
                {
                    "status":
                        "no_mailbox",

                    "error": (
                        "Other Work Email mailbox "
                        "is unavailable."
                    ),
                },
                status=(
                    status.HTTP_404_NOT_FOUND
                ),
            )

        if (
            not account.is_credential_valid()
            or
            not account.credential_ciphertext
        ):
            return Response(
                {
                    "status":
                        "reauth_required",

                    "error": (
                        "Mailbox credential requires "
                        "reconfiguration."
                    ),
                },
                status=(
                    status.HTTP_409_CONFLICT
                ),
            )

        from inbox.tasks import (
            sync_email_account,
        )

        try:
            sync_email_account.delay(
                account.id
            )

        except Exception:
            return Response(
                {
                    "status":
                        "queue_failed",

                    "error": (
                        "Unable to start Other Work "
                        "Email synchronization."
                    ),

                    "action": (
                        "Try again shortly. If the "
                        "problem continues, contact "
                        "your One UCH administrator."
                    ),
                },
                status=(
                    status.HTTP_503_SERVICE_UNAVAILABLE
                ),
            )

        return Response(
            {
                "status":
                    "sync_queued",

                "provider":
                    "imap",

                "email_account_id":
                    account.id,

                "message": (
                    "Other Work Email "
                    "synchronization started."
                ),
            },
            status=(
                status.HTTP_202_ACCEPTED
            ),
        )
