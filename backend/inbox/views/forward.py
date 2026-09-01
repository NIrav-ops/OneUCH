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
        + value
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


    cc_addresses = [
        str(
            item.get(
                "email",
                "",
            )
        )
        .strip()

        for item
        in (
            source_recipient_meta.get(
                "cc",
                [],
            )
            or []
        )

        if (
            isinstance(
                item,
                dict,
            )
            and
            item.get(
                "email"
            )
        )
    ]


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
        (
            "To: "
            +
            str(
                source.recipients
                or ""
            )
        ),
    ]


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


    def post(
        self,
        request,
        message_id,
    ):
        source = (
            InboxMessage.objects
            .select_related(
                "email_account",
                "conversation",
            )
            .filter(
                id=message_id,
                user=request.user,
                is_draft=False,
            )
            .exclude(
                folder="trash"
            )
            .first()
        )


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

            # A forward must use the mailbox that owns
            # the source message.
            "account_id":
                account.id,
        }


        response = (
            UnifiedSendMessageAPIView()
            .send_with_data(
                request=request,
                data=payload,
                signature_already_applied=True,
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

            source_attachment_count = (
                len(
                    source.attachment_meta
                    or []
                )
            )


            response.data[
                "source_attachment_count"
            ] = (
                source_attachment_count
            )


            # Attachment forwarding is intentionally explicit.
            # Current provider-native attachment download remains
            # available, and advanced attachment-forwarding can
            # be completed in Gmail/Outlook through Open Provider.
            response.data[
                "attachments_forwarded"
            ] = False


        return response
