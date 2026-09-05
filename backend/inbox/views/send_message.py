from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from django.utils import timezone

from asgiref.sync import async_to_sync

from channels.layers import get_channel_layer

from googleapiclient.discovery import build

from email.mime.text import MIMEText

from email.mime.multipart import (
    MIMEMultipart,
)

from email.mime.base import (
    MIMEBase,
)

from email import (
    encoders,
)

import base64
import requests

from inbox.models import (
    Conversation,
    InboxMessage,
)

from inbox.services.recipient_payload import (
    graph_recipient_payload,
    mime_recipient_header,
    normalize_recipient_buckets,
)

from email_accounts.services.signatures import (
    apply_account_signature,
)

from inbox.services.outbound_attachments import (
    attachment_metadata,
    prepare_outbound_attachments,
)

from inbox.services.outbound_idempotency import (
    OutboundIdempotencyConflict,
    OutboundIdempotencyUnavailable,
    build_outbound_fingerprint,
    claim_outbound_intent,
    complete_outbound_intent,
    get_outbound_intent,
    replay_outbound_intent,
    resolve_outbound_idempotency_key,
)

from googleapis.utils import (
    get_gmail_credentials,
)

from microsoftapis.utils import (
    get_microsoft_access_token,
)

from inbox.utils.conversation_key import (
    generate_conversation_key,
)

from platform_core.api.tenant import (
    get_user_organization_or_404,
)


class UnifiedSendMessageAPIView(
    APIView
):
    permission_classes = [
        IsAuthenticated
    ]


    def post(
        self,
        request,
    ):
        return self.send_with_data(
            request=request,
            data=request.data,
        )


    def send_with_data(
        self,
        *,
        request,
        data,
        signature_already_applied=False,
        prepared_attachments=None,
        idempotency_key=None,
        idempotency_operation="send",
    ):

        try:

            user = request.user

            organization = (
                get_user_organization_or_404(
                    request
                )
            )

            subject = data.get(
                "subject",
                "",
            )

            body = data.get(
                "body",
                "",
            )

            conversation_id = (
                data.get(
                    "conversation_id"
                )
            )


            try:

                (
                    recipient_meta,
                    recipients_flat,
                ) = (
                    normalize_recipient_buckets(
                        to=data.get(
                            "to"
                        ),
                        cc=data.get(
                            "cc",
                            []
                        ),
                        bcc=data.get(
                            "bcc",
                            []
                        ),
                        require_to=True,
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


            to_recipients = (
                recipient_meta[
                    "to"
                ]
            )

            cc_recipients = (
                recipient_meta[
                    "cc"
                ]
            )

            bcc_recipients = (
                recipient_meta[
                    "bcc"
                ]
            )


            to_flat = ", ".join(
                item[
                    "email"
                ]
                for item
                in to_recipients
            )


            # =========================
            # ACCOUNT
            # =========================

            account_id = data.get(
                "account_id"
            )


            if account_id:

                account = (
                    user.email_accounts
                    .filter(
                        id=account_id
                    )
                    .first()
                )

            else:

                account = (
                    user.email_accounts
                    .first()
                )


            if not account:

                return Response(
                    {
                        "error":
                            "No email account connected"
                    },
                    status=400,
                )


            account_type = (
                account.account_type
            )


            try:

                if prepared_attachments is None:

                    outbound_attachments = (
                        prepare_outbound_attachments(
                            request=request,
                            account=account,
                        )
                    )

                else:

                    outbound_attachments = list(
                        prepared_attachments
                    )

            except ValueError as exc:

                return Response(
                    {
                        "error":
                            str(exc)
                    },
                    status=400,
                )


            outbound_attachment_meta = (
                attachment_metadata(
                    outbound_attachments
                )
            )


            sender_email = (
                str(
                    account.email_address
                )
                .strip()
                .lower()
            )


            sender_meta = {
                "name":
                    "",

                "email":
                    sender_email,
            }


            if not signature_already_applied:

                body = (
                    apply_account_signature(
                        account=account,
                        body=body,
                    )
                )


            # =========================
            # IDEMPOTENCY PRE-RESOLUTION
            # =========================
            #
            # Resolve an existing semantic send BEFORE local
            # conversation lookup. Provider synchronization is
            # allowed to upgrade conversation_key to a native
            # Gmail/Graph thread identity; that must not cause
            # a same-key retry to generate a new conversation.

            try:

                outbound_idempotency_key = (
                    resolve_outbound_idempotency_key(
                        request=request,
                        explicit=(
                            idempotency_key
                        ),
                    )
                )

            except OutboundIdempotencyConflict as exc:

                return Response(
                    {
                        "error":
                            str(exc)
                    },
                    status=409,
                )


            existing_outbound_intent = None


            if outbound_idempotency_key:

                try:

                    existing_outbound_intent = (
                        get_outbound_intent(
                            user_id=user.id,
                            idempotency_key=(
                                outbound_idempotency_key
                            ),
                        )
                    )

                except OutboundIdempotencyUnavailable as exc:

                    return Response(
                        {
                            "error":
                                str(exc)
                        },
                        status=503,
                    )


            # =========================
            # CONVERSATION
            # =========================

            conversation = None


            # New Compose has no explicit conversation_id.
            #
            # If this is a replay, the original idempotency
            # record already points at the local Sent message.
            # Reuse that message's exact conversation instead of
            # regenerating a local conversation key that provider
            # reconciliation may already have upgraded.
            if (
                conversation_id is None
                and
                existing_outbound_intent
                and
                existing_outbound_intent.get(
                    "message_id"
                )
                is not None
            ):

                original_intent_message = (
                    InboxMessage.objects
                    .filter(
                        id=(
                            existing_outbound_intent[
                                "message_id"
                            ]
                        ),
                        user=user,
                        organization=organization,
                        email_account=account,
                    )
                    .select_related(
                        "conversation"
                    )
                    .first()
                )


                if (
                    original_intent_message
                    and
                    original_intent_message
                    .conversation_id
                ):

                    conversation = (
                        original_intent_message
                        .conversation
                    )


            if conversation_id:

                conversation = (
                    Conversation.objects
                    .filter(
                        id=conversation_id,
                        user=user,
                        organization=organization,
                    )
                    .first()
                )


                if not conversation:

                    return Response(
                        {
                            "error":
                                "Conversation not found"
                        },
                        status=404,
                    )


            if conversation is None:

                conversation_key = (
                    generate_conversation_key(
                        account_type,
                        None,
                        subject,
                        to_flat,
                    )
                )


                conversation, _ = (
                    Conversation.objects
                    .get_or_create(
                        user=user,
                        organization=organization,
                        conversation_key=(
                            conversation_key
                        ),
                        defaults={
                            "subject":
                                (
                                    subject
                                    or
                                    "New Message"
                                ),

                            "email_account":
                                account,

                            "last_message_preview":
                                "",
                        },
                    )
                )


            # =========================
            # IDEMPOTENCY RESERVATION
            # =========================

            if outbound_idempotency_key:

                fingerprint = (
                    build_outbound_fingerprint(
                        operation=(
                            idempotency_operation
                        ),
                        payload={
                            "account_id":
                                account.id,

                            "conversation_id":
                                conversation.id,

                            "recipient_meta":
                                recipient_meta,

                            "subject":
                                subject,

                            "body":
                                body,
                        },
                        attachments=(
                            outbound_attachments
                        ),
                    )
                )


                try:

                    (
                        intent,
                        intent_created,
                    ) = (
                        claim_outbound_intent(
                            user_id=user.id,
                            idempotency_key=(
                                outbound_idempotency_key
                            ),
                            operation=(
                                idempotency_operation
                            ),
                            fingerprint=(
                                fingerprint
                            ),
                        )
                    )

                except OutboundIdempotencyConflict as exc:

                    return Response(
                        {
                            "error":
                                str(exc)
                        },
                        status=409,
                    )

                except OutboundIdempotencyUnavailable as exc:

                    return Response(
                        {
                            "error":
                                str(exc)
                        },
                        status=503,
                    )


                if not intent_created:

                    (
                        replay_payload,
                        replay_status,
                    ) = (
                        replay_outbound_intent(
                            intent
                        )
                    )


                    return Response(
                        replay_payload,
                        status=replay_status,
                    )


            # =========================
            # PROVIDER SEND
            # =========================

            provider_message_id = (
                "sent"
            )


            if account_type == "gmail":

                creds = (
                    get_gmail_credentials(
                        user
                    )
                )


                service = build(
                    "gmail",
                    "v1",
                    credentials=creds,
                )


                if outbound_attachments:

                    message = (
                        MIMEMultipart()
                    )

                    message.attach(
                        MIMEText(
                            body
                        )
                    )


                    for item in (
                        outbound_attachments
                    ):

                        content_type = (
                            item[
                                "content_type"
                            ]
                        )


                        if "/" in content_type:

                            main_type, sub_type = (
                                content_type.split(
                                    "/",
                                    1,
                                )
                            )

                        else:

                            main_type = (
                                "application"
                            )

                            sub_type = (
                                "octet-stream"
                            )


                        part = MIMEBase(
                            main_type,
                            sub_type,
                        )

                        part.set_payload(
                            item[
                                "content"
                            ]
                        )

                        encoders.encode_base64(
                            part
                        )

                        part.add_header(
                            "Content-Disposition",
                            "attachment",
                            filename=(
                                item[
                                    "filename"
                                ]
                            ),
                        )

                        message.attach(
                            part
                        )

                else:

                    message = MIMEText(
                        body
                    )


                message[
                    "To"
                ] = (
                    mime_recipient_header(
                        to_recipients
                    )
                )


                if cc_recipients:

                    message[
                        "Cc"
                    ] = (
                        mime_recipient_header(
                            cc_recipients
                        )
                    )


                if bcc_recipients:

                    message[
                        "Bcc"
                    ] = (
                        mime_recipient_header(
                            bcc_recipients
                        )
                    )


                message[
                    "Subject"
                ] = subject


                raw = (
                    base64
                    .urlsafe_b64encode(
                        message.as_bytes()
                    )
                    .decode()
                )


                gmail_result = (
                    service.users()
                    .messages()
                    .send(
                        userId="me",
                        body={
                            "raw":
                                raw
                        },
                    )
                    .execute()
                )


                provider_message_id = (
                    gmail_result.get(
                        "id"
                    )
                    or
                    "sent"
                )


            elif account_type == "outlook":

                token = (
                    get_microsoft_access_token(
                        user
                    )
                )


                graph_attachments = [
                    {
                        "@odata.type":
                            "#microsoft.graph.fileAttachment",

                        "name":
                            item[
                                "filename"
                            ],

                        "contentType":
                            item[
                                "content_type"
                            ],

                        "contentBytes":
                            (
                                base64
                                .b64encode(
                                    item[
                                        "content"
                                    ]
                                )
                                .decode(
                                    "ascii"
                                )
                            ),
                    }

                    for item
                    in outbound_attachments
                ]


                graph_message = {
                    "subject":
                        subject,

                    "body": {
                        "contentType":
                            "Text",

                        "content":
                            body,
                    },

                    "toRecipients":
                        graph_recipient_payload(
                            to_recipients
                        ),

                    "ccRecipients":
                        graph_recipient_payload(
                            cc_recipients
                        ),

                    "bccRecipients":
                        graph_recipient_payload(
                            bcc_recipients
                        ),
                }


                if graph_attachments:

                    graph_message[
                        "attachments"
                    ] = (
                        graph_attachments
                    )


                response = requests.post(
                    (
                        "https://graph.microsoft.com/"
                        "v1.0/me/sendMail"
                    ),
                    headers={
                        "Authorization":
                            f"Bearer {token}",

                        "Content-Type":
                            "application/json",
                    },
                    json={
                        "message":
                            graph_message
                    },
                    timeout=30,
                )


                if response.status_code >= 400:

                    try:

                        graph_error = (
                            response.json()
                        )

                        graph_message_text = (
                            graph_error
                            .get(
                                "error",
                                {},
                            )
                            .get(
                                "message"
                            )
                        )

                    except Exception:

                        graph_message_text = (
                            None
                        )


                    raise Exception(
                        "Microsoft Graph sendMail failed "
                        f"with status {response.status_code}"
                        +
                        (
                            f": {graph_message_text}"
                            if graph_message_text
                            else ""
                        )
                    )


            else:

                return Response(
                    {
                        "error":
                            "Unsupported email account type"
                    },
                    status=400,
                )


            # =========================
            # LOCAL SENT MATERIALIZATION
            # =========================

            message_obj = (
                InboxMessage.objects
                .create(
                    user=user,
                    organization=organization,
                    platform=(
                        account_type
                    ),
                    folder="sent",
                    external_message_id=(
                        provider_message_id
                    ),
                    sender=(
                        sender_email
                    ),
                    sender_meta=(
                        sender_meta
                    ),
                    recipients=(
                        recipients_flat
                    ),
                    recipient_meta=(
                        recipient_meta
                    ),
                    subject=(
                        subject
                        or
                        "No Subject"
                    ),
                    body=body,
                    attachment_meta=(
                        outbound_attachment_meta
                    ),
                    is_read=True,
                    email_account=(
                        account
                    ),
                    direction="outbound",
                    is_draft=False,
                    status="sent",
                    received_at=(
                        timezone.now()
                    ),
                    conversation=(
                        conversation
                    ),
                )
            )


            conversation.last_message = (
                message_obj
            )

            conversation.last_message_at = (
                message_obj.received_at
            )

            conversation.last_message_preview = (
                body[
                    :120
                ]
                if body
                else ""
            )

            conversation.save()


            response_payload = {
                "status":
                    "sent",

                "conversation_id":
                    conversation.id,

                "message_id":
                    message_obj.id,

                "attachment_count":
                    len(
                        outbound_attachments
                    ),
            }


            # Complete the semantic send intent before optional
            # realtime notification work. If websocket delivery
            # fails after the provider accepted the mail, a client
            # retry with the same key returns this prior result
            # instead of contacting the provider again.
            if outbound_idempotency_key:

                try:

                    complete_outbound_intent(
                        user_id=user.id,
                        idempotency_key=(
                            outbound_idempotency_key
                        ),
                        message_id=(
                            message_obj.id
                        ),
                        provider_message_id=(
                            provider_message_id
                        ),
                        response_data=(
                            response_payload
                        ),
                        http_status=200,
                    )

                except OutboundIdempotencyUnavailable as exc:

                    # The provider has already accepted the mail
                    # and the local Sent row exists. Fail closed:
                    # the original processing reservation remains
                    # and prevents an automatic duplicate send.
                    return Response(
                        {
                            **response_payload,

                            "warning": (
                                "Message was sent, but delivery "
                                "safety state could not be finalized."
                            ),

                            "idempotency_error":
                                str(exc),
                        },
                        status=200,
                    )


            # =========================
            # REALTIME UPDATE
            # =========================

            channel_layer = (
                get_channel_layer()
            )


            async_to_sync(
                channel_layer.group_send
            )(
                f"inbox_{user.id}",
                {
                    "type":
                        "send_update",

                    "data": {
                        "message":
                            "new_email"
                    },
                },
            )


            return Response(
                response_payload
            )


        except Exception as exc:

            import traceback

            traceback.print_exc()

            return Response(
                {
                    "error":
                        str(exc)
                },
                status=500,
            )
