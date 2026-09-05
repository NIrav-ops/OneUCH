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

from inbox.views.send_message import (
    UnifiedSendMessageAPIView,
)

from email_accounts.services.signatures import (
    apply_account_signature,
)

from inbox.services.forward_attachments import (
    ForwardAttachmentProviderError,
    prepare_forward_attachments,
    serialize_forward_source_attachments,
)

from platform_core.api.tenant import (
    get_user_organization_or_404,
)


def _forward_subject(
    source_subject,
):
    value = (
        str(
            source_subject
            or
            "No Subject"
        )
        .strip()
    )


    if value.lower().startswith(
        "fwd:"
    ):

        return value


    return (
        "Fwd: "
        +
        value
    )


def _forwarded_body(
    *,
    source,
    note,
):
    source_recipient_meta = (
        source.recipient_meta
        if isinstance(
            source.recipient_meta,
            dict,
        )
        else {}
    )


    # Intentionally only materialize To and Cc from the source.
    # Bcc is private envelope information and must never be
    # disclosed to the new forwarding recipient.
    def bucket_addresses(
        bucket,
    ):
        values = []

        seen = set()


        for item in (
            source_recipient_meta.get(
                bucket,
                [],
            )
            or []
        ):

            if not isinstance(
                item,
                dict,
            ):
                continue


            email_value = (
                str(
                    item.get(
                        "email",
                        "",
                    )
                )
                .strip()
                .lower()
            )


            if (
                not email_value
                or
                email_value in seen
            ):
                continue


            seen.add(
                email_value
            )

            values.append(
                email_value
            )


        return values


    to_addresses = (
        bucket_addresses(
            "to"
        )
    )


    cc_addresses = (
        bucket_addresses(
            "cc"
        )
    )


    # Do not use the legacy flat `source.recipients` field in
    # quoted Forward headers. Modern sync intentionally flattens
    # To + Cc + Bcc into that compatibility field, so using it
    # here could disclose a source Bcc recipient.
    lines = [
        "---------- Forwarded message ----------",
        (
            "From: "
            +
            str(
                source.sender
                or ""
            )
        ),
        (
            "Date: "
            +
            (
                source.received_at
                .isoformat()
                if source.received_at
                else ""
            )
        ),
        (
            "Subject: "
            +
            str(
                source.subject
                or
                "No Subject"
            )
        ),
    ]


    if to_addresses:

        lines.append(
            "To: "
            +
            ", ".join(
                to_addresses
            )
        )


    if cc_addresses:

        lines.append(
            "Cc: "
            +
            ", ".join(
                cc_addresses
            )
        )


    lines.extend(
        [
            "",
            str(
                source.body
                or ""
            ),
        ]
    )


    forwarded = (
        "\n".join(
            lines
        )
        .strip()
    )


    note_value = (
        str(
            note
            or ""
        )
        .strip()
    )


    if note_value:

        return (
            note_value
            +
            "\n\n"
            +
            forwarded
        )


    return forwarded


class ForwardMessageAPIView(
    APIView
):
    permission_classes = [
        IsAuthenticated
    ]


    def _source(
        self,
        request,
        message_id,
    ):
        organization = (
            get_user_organization_or_404(
                request
            )
        )

        return (
            InboxMessage.objects
            .select_related(
                "email_account",
                "conversation",
            )
            .prefetch_related(
                "attachments"
            )
            .filter(
                id=message_id,
                user=request.user,
                organization=organization,
                is_draft=False,
            )
            .exclude(
                folder="trash"
            )
            .first()
        )


    def _account_error(
        self,
        request,
        source,
    ):
        if source is None:

            return Response(
                {
                    "error":
                        "Message not found"
                },
                status=404,
            )


        account = (
            source.email_account
        )


        if (
            account is None
            or
            account.user_id
            !=
            request.user.id
            or
            not account.is_active
        ):

            return Response(
                {
                    "error":
                        "Original mailbox is not available"
                },
                status=400,
            )


        return None


    def get(
        self,
        request,
        message_id,
    ):
        """
        Read-only Forward preflight.

        The frontend uses this to display the original files that
        are selected by default. No provider content is downloaded
        during preflight.
        """
        source = (
            self._source(
                request,
                message_id,
            )
        )


        error = (
            self._account_error(
                request,
                source,
            )
        )


        if error is not None:
            return error


        source_attachments = (
            serialize_forward_source_attachments(
                source
            )
        )


        return Response(
            {
                "message_id":
                    source.id,

                "account_id":
                    source.email_account_id,

                "source_attachment_count":
                    len(
                        source_attachments
                    ),

                "source_attachments":
                    source_attachments,

                "attachments_forwarded_by_default":
                    True,
            }
        )


    def post(
        self,
        request,
        message_id,
    ):
        source = (
            self._source(
                request,
                message_id,
            )
        )


        error = (
            self._account_error(
                request,
                source,
            )
        )


        if error is not None:
            return error


        account = (
            source.email_account
        )


        subject = (
            str(
                request.data.get(
                    "subject"
                )
                or ""
            )
            .strip()
            or
            _forward_subject(
                source.subject
            )
        )


        signed_note = (
            apply_account_signature(
                account=account,
                body=(
                    request.data.get(
                        "body",
                        "",
                    )
                ),
            )
        )


        payload = {
            "to":
                request.data.get(
                    "to"
                ),

            "cc":
                request.data.get(
                    "cc",
                    [],
                ),

            "bcc":
                request.data.get(
                    "bcc",
                    [],
                ),

            "subject":
                subject,

            "body":
                _forwarded_body(
                    source=source,
                    note=signed_note,
                ),

            # Forward remains bound to the mailbox that owns
            # the original message.
            "account_id":
                account.id,
        }


        try:

            prepared = (
                prepare_forward_attachments(
                    request=request,
                    source=source,
                    account=account,
                )
            )


        except ValueError as exc:

            return Response(
                {
                    "error":
                        str(exc)
                },
                status=400,
            )


        except ForwardAttachmentProviderError as exc:

            return Response(
                {
                    "error":
                        str(exc)
                },
                status=502,
            )


        response = (
            UnifiedSendMessageAPIView()
            .send_with_data(
                request=request,
                data=payload,
                signature_already_applied=True,
                prepared_attachments=(
                    prepared[
                        "attachments"
                    ]
                ),
                idempotency_operation=(
                    "forward"
                ),
            )
        )


        if (
            response.status_code
            <
            400
            and
            isinstance(
                response.data,
                dict,
            )
        ):

            response.data[
                "source_attachment_count"
            ] = (
                prepared[
                    "source_attachment_count"
                ]
            )


            response.data[
                "source_attachments_forwarded"
            ] = (
                prepared[
                    "source_attachments_forwarded"
                ]
            )


            response.data[
                "user_attachment_count"
            ] = (
                prepared[
                    "user_attachment_count"
                ]
            )


            response.data[
                "attachments_forwarded"
            ] = (
                prepared[
                    "source_attachments_forwarded"
                ]
                >
                0
            )


        return response
