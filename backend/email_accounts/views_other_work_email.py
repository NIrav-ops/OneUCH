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
