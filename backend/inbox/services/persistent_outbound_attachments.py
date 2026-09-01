from django.core.files.base import (
    ContentFile,
)

from inbox.models import (
    Attachment,
)

from inbox.services.outbound_attachments import (
    MAX_OUTBOUND_FILES,
    effective_attachment_limit_bytes,
)


def _delete_attachment_record(
    attachment,
):
    """
    Delete both storage content and its database record.

    Django does not automatically remove FileField content when
    a model row is deleted, so cleanup must be explicit.
    """
    try:

        if (
            attachment.file
            and
            attachment.file.name
        ):
            attachment.file.delete(
                save=False
            )

    finally:

        if attachment.pk:
            attachment.delete()


def persist_outbound_attachments(
    *,
    message,
    prepared,
):
    """
    Persist already-governed outbound attachment payloads.

    Provider delivery happens asynchronously for Reply/Reply-All,
    therefore request-memory bytes cannot be passed through Celery.

    The persisted Attachment rows remain bound to the governed
    InboxMessage and can later be reused by Draft/Forward flows.
    """
    prepared = (
        prepared
        or []
    )


    if not prepared:
        return []


    if (
        len(
            prepared
        )
        >
        MAX_OUTBOUND_FILES
    ):
        raise ValueError(
            "A maximum of 10 attachments can be sent at once."
        )


    created = []


    try:

        for item in prepared:

            attachment = (
                Attachment(
                    message=message,
                    filename=(
                        item[
                            "filename"
                        ]
                    ),
                    content_type=(
                        item[
                            "content_type"
                        ]
                    ),
                    size=(
                        item[
                            "size"
                        ]
                    ),
                    policy_violated=False,
                )
            )


            try:

                attachment.file.save(
                    item[
                        "filename"
                    ],
                    ContentFile(
                        item[
                            "content"
                        ]
                    ),
                    save=False,
                )

                attachment.save()

                created.append(
                    attachment
                )

            except Exception:

                _delete_attachment_record(
                    attachment
                )

                raise


        return created


    except Exception:

        for attachment in reversed(
            created
        ):

            _delete_attachment_record(
                attachment
            )

        raise


def load_persisted_outbound_attachments(
    *,
    message,
):
    """
    Rehydrate persisted outbound files immediately before
    provider delivery.

    Governance is rechecked at delivery time as well as upload
    time so a changed organization policy cannot silently permit
    an attachment that is no longer allowed.
    """
    records = list(
        message.attachments
        .all()
        .order_by(
            "id"
        )
    )


    if not records:
        return []


    if (
        len(
            records
        )
        >
        MAX_OUTBOUND_FILES
    ):
        raise ValueError(
            "Persisted attachment count exceeds the outbound limit."
        )


    account = (
        message.email_account
    )


    if account is None:
        raise ValueError(
            "Reply attachment delivery requires the original mailbox."
        )


    limit = (
        effective_attachment_limit_bytes(
            account=account,
            user=message.user,
        )
    )


    total = 0

    prepared = []


    for attachment in records:

        if (
            not attachment.file
            or
            not attachment.file.name
        ):
            raise ValueError(
                "Persisted attachment file is unavailable."
            )


        attachment.file.open(
            "rb"
        )

        try:

            content = (
                attachment.file.read()
            )

        finally:

            attachment.file.close()


        size = len(
            content
        )


        if size <= 0:
            raise ValueError(
                f"{attachment.filename} is empty."
            )


        total += size


        if total > limit:

            raise ValueError(
                "Persisted attachments now exceed "
                "the active outbound attachment policy."
            )


        prepared.append(
            {
                "filename":
                    attachment.filename,

                "content_type":
                    (
                        attachment.content_type
                        or
                        "application/octet-stream"
                    ),

                "size":
                    size,

                "content":
                    content,
            }
        )


    return prepared
