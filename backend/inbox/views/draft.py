import json

from django.db import transaction
from django.utils import timezone

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from email_accounts.models import (
    EmailAccount,
)

from inbox.models import (
    Conversation,
    InboxMessage,
)

from inbox.services.outbound_attachments import (
    prepare_outbound_attachments,
)

from inbox.services.persistent_outbound_attachments import (
    serialize_persisted_outbound_attachments,
    synchronize_persisted_outbound_attachments,
    validate_persisted_outbound_selection,
)

from inbox.services.recipient_payload import (
    normalize_recipient_buckets,
)


def _parse_retained_attachment_ids(
    data,
):
    if (
        "retained_attachment_ids"
        not in data
    ):
        return None


    raw = data.get(
        "retained_attachment_ids"
    )


    if raw in (
        None,
        "",
    ):
        return []


    if isinstance(
        raw,
        (
            list,
            tuple,
        ),
    ):

        values = list(
            raw
        )

    else:

        text = str(
            raw
        ).strip()


        try:

            decoded = json.loads(
                text
            )

        except json.JSONDecodeError:

            decoded = [
                item.strip()
                for item
                in text.split(
                    ","
                )
                if item.strip()
            ]


        if isinstance(
            decoded,
            list,
        ):

            values = decoded

        else:

            values = [
                decoded
            ]


    result = []


    for value in values:

        try:

            attachment_id = int(
                value
            )

        except (
            TypeError,
            ValueError,
        ) as exc:

            raise ValueError(
                "Invalid retained draft attachment id."
            ) from exc


        if attachment_id not in result:

            result.append(
                attachment_id
            )


    return result


class DraftSaveAPIView(
    APIView
):
    permission_classes = [
        IsAuthenticated
    ]


    def post(
        self,
        request,
    ):
        draft_id = (
            request.data.get(
                "draft_id"
            )
        )


        conversation_id = (
            request.data.get(
                "conversation_id"
            )
        )


        existing_draft = None

        conversation = None


        if draft_id:

            existing_draft = (
                InboxMessage.objects
                .filter(
                    id=draft_id,
                    user=request.user,
                    is_draft=True,
                )
                .select_related(
                    "conversation",
                    "email_account",
                )
                .prefetch_related(
                    "attachments"
                )
                .first()
            )


            if existing_draft is None:

                return Response(
                    {
                        "error":
                            "Draft not found"
                    },
                    status=(
                        status
                        .HTTP_404_NOT_FOUND
                    ),
                )


            conversation = (
                existing_draft.conversation
            )


            if (
                conversation_id
                and
                str(
                    existing_draft
                    .conversation_id
                )
                !=
                str(
                    conversation_id
                )
            ):

                return Response(
                    {
                        "error":
                            "Draft conversation mismatch"
                    },
                    status=400,
                )


        elif conversation_id:

            conversation = (
                Conversation.objects
                .filter(
                    id=conversation_id,
                    user=request.user,
                )
                .first()
            )


            if conversation is None:

                return Response(
                    {
                        "error":
                            "Conversation not found"
                    },
                    status=(
                        status
                        .HTTP_404_NOT_FOUND
                    ),
                )


            existing_draft = (
                InboxMessage.objects
                .filter(
                    user=request.user,
                    conversation=conversation,
                    is_draft=True,
                )
                .select_related(
                    "email_account"
                )
                .prefetch_related(
                    "attachments"
                )
                .first()
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


        if "to" in request.data:

            to_source = (
                request.data.get(
                    "to"
                )
            )

        else:

            to_source = (
                request.data.get(
                    "recipients",
                    "",
                )
            )


        try:

            (
                recipient_meta,
                recipients_flat,
            ) = (
                normalize_recipient_buckets(
                    to=to_source,
                    cc=request.data.get(
                        "cc",
                        [],
                    ),
                    bcc=request.data.get(
                        "bcc",
                        [],
                    ),
                    require_to=False,
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


        email_account_id = (
            request.data.get(
                "email_account_id"
            )
            or
            request.data.get(
                "account_id"
            )
        )


        if email_account_id:

            email_account = (
                EmailAccount.objects
                .filter(
                    id=email_account_id,
                    user=request.user,
                )
                .first()
            )


            if email_account is None:

                return Response(
                    {
                        "error":
                            "Email account not found"
                    },
                    status=(
                        status
                        .HTTP_404_NOT_FOUND
                    ),
                )

        else:

            email_account = (
                EmailAccount.objects
                .filter(
                    user=request.user
                )
                .first()
            )


        if (
            getattr(
                request,
                "FILES",
                None,
            )
            and
            request.FILES.getlist(
                "attachments"
            )
            and
            email_account is None
        ):

            return Response(
                {
                    "error":
                        "Select the sending mailbox before saving attachments."
                },
                status=400,
            )


        try:

            prepared = (
                prepare_outbound_attachments(
                    request=request,
                    account=email_account,
                )
                if email_account
                else []
            )


            retained_ids = (
                _parse_retained_attachment_ids(
                    request.data
                )
            )


            existing_records = (
                list(
                    existing_draft
                    .attachments
                    .all()
                    .order_by(
                        "id"
                    )
                )
                if existing_draft
                else []
            )


            if retained_ids is None:

                retained_ids = [
                    record.id
                    for record
                    in existing_records
                ]


            existing_by_id = {
                record.id:
                    record
                for record
                in existing_records
            }


            retained_records = []


            for attachment_id in retained_ids:

                if (
                    attachment_id
                    not in
                    existing_by_id
                ):

                    raise ValueError(
                        "A retained draft attachment does not belong "
                        "to this draft."
                    )


                retained_records.append(
                    existing_by_id[
                        attachment_id
                    ]
                )


            validate_persisted_outbound_selection(
                account=email_account,
                user=request.user,
                records=retained_records,
                prepared=prepared,
            )


        except ValueError as exc:

            return Response(
                {
                    "error":
                        str(exc)
                },
                status=400,
            )


        organization = (
            request.user
            .organization_membership
            .organization
        )


        try:

            with transaction.atomic():

                if conversation is None:

                    conversation = (
                        Conversation.objects
                        .create(
                            user=request.user,
                            organization=(
                                organization
                            ),
                            subject=(
                                subject
                                or
                                "Draft"
                            ),
                            conversation_key=(
                                "draft_"
                                +
                                str(
                                    request.user.id
                                )
                                +
                                "_"
                                +
                                str(
                                    timezone
                                    .now()
                                    .timestamp()
                                )
                            ),
                            email_account=(
                                email_account
                            ),
                        )
                    )


                sender_email = (
                    email_account.email_address
                    if email_account
                    else request.user.email
                )


                now = timezone.now()


                if existing_draft is None:

                    draft = (
                        InboxMessage.objects
                        .create(
                            user=request.user,
                            organization=(
                                organization
                            ),
                            platform=(
                                email_account
                                .account_type
                                if email_account
                                else "gmail"
                            ),
                            direction="outbound",
                            email_account=(
                                email_account
                            ),
                            conversation=(
                                conversation
                            ),
                            sender=(
                                sender_email
                            ),
                            sender_meta={
                                "name":
                                    "",

                                "email":
                                    str(
                                        sender_email
                                    )
                                    .strip()
                                    .lower(),
                            },
                            recipients=(
                                recipients_flat
                            ),
                            recipient_meta=(
                                recipient_meta
                            ),
                            subject=subject,
                            body=body,
                            received_at=now,
                            folder="draft",
                            is_draft=True,
                            status="queued",
                            external_message_id=(
                                "draft-"
                                +
                                str(
                                    conversation.id
                                )
                            ),
                        )
                    )

                else:

                    draft = existing_draft

                    draft.organization = (
                        organization
                    )

                    draft.platform = (
                        email_account.account_type
                        if email_account
                        else draft.platform
                    )

                    draft.direction = (
                        "outbound"
                    )

                    draft.email_account = (
                        email_account
                    )

                    draft.sender = (
                        sender_email
                    )

                    draft.sender_meta = {
                        "name":
                            "",

                        "email":
                            str(
                                sender_email
                            )
                            .strip()
                            .lower(),
                    }

                    draft.recipients = (
                        recipients_flat
                    )

                    draft.recipient_meta = (
                        recipient_meta
                    )

                    draft.subject = subject

                    draft.body = body

                    draft.received_at = now

                    draft.folder = "draft"

                    draft.is_draft = True

                    draft.status = "queued"

                    draft.save()


                final_records = (
                    synchronize_persisted_outbound_attachments(
                        message=draft,
                        retained_ids=(
                            retained_ids
                        ),
                        prepared=prepared,
                    )
                )


                conversation.last_message = (
                    draft
                )

                conversation.last_message_at = (
                    draft.received_at
                )

                conversation.last_message_preview = (
                    draft.body[
                        :120
                    ]
                    if draft.body
                    else ""
                )

                conversation.email_account = (
                    email_account
                )

                conversation.save()


        except ValueError as exc:

            return Response(
                {
                    "error":
                        str(exc)
                },
                status=400,
            )


        except Exception:

            return Response(
                {
                    "error":
                        "Unable to persist draft attachments."
                },
                status=500,
            )


        return Response(
            {
                "status":
                    "draft_saved",

                "draft_id":
                    draft.id,

                "conversation_id":
                    conversation.id,

                "attachment_count":
                    len(
                        final_records
                    ),

                "attachments":
                    serialize_persisted_outbound_attachments(
                        draft
                    ),
            },
            status=(
                status
                .HTTP_200_OK
            ),
        )


class DraftListAPIView(
    APIView
):
    permission_classes = [
        IsAuthenticated
    ]


    def get(
        self,
        request,
    ):

        drafts = (
            InboxMessage.objects
            .filter(
                user=request.user,
                is_draft=True,
            )
            .select_related(
                "conversation",
                "email_account",
            )
            .prefetch_related(
                "attachments"
            )
            .order_by(
                "-received_at"
            )
        )


        data = [
            {
                "id":
                    draft.id,

                "conversation_id":
                    (
                        draft.conversation.id
                        if draft.conversation
                        else None
                    ),

                "subject":
                    draft.subject,

                "recipients":
                    draft.recipients,

                "recipient_meta":
                    draft.recipient_meta,

                "body":
                    draft.body,

                "email_account_id":
                    (
                        draft.email_account.id
                        if draft.email_account
                        else None
                    ),

                "attachments":
                    serialize_persisted_outbound_attachments(
                        draft
                    ),

                "attachment_count":
                    draft.attachments.count(),

                "updated_at":
                    draft.received_at,
            }

            for draft
            in drafts
        ]


        return Response(
            data
        )
