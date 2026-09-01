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



def serialize_persisted_outbound_attachments(
    message,
):
    """
    Stable draft/UI representation.

    Provider-native attachment IDs do not exist yet because
    these files are stored by One UCH until the user sends.
    """
    return [
        {
            "id":
                attachment.id,

            "filename":
                attachment.filename,

            "content_type":
                (
                    attachment.content_type
                    or
                    "application/octet-stream"
                ),

            "size":
                attachment.size,

            "saved":
                True,
        }

        for attachment
        in (
            message.attachments
            .all()
            .order_by(
                "id"
            )
        )
    ]


def _persistent_attachment_meta(
    records,
):
    return [
        {
            "filename":
                record.filename,

            "mime_type":
                (
                    record.content_type
                    or
                    "application/octet-stream"
                ),

            "size":
                record.size,

            "attachment_id":
                None,

            "outbound":
                True,
        }

        for record
        in records
    ]


def validate_persisted_outbound_selection(
    *,
    account,
    user,
    records,
    prepared,
):
    """
    Validate the complete saved-draft attachment set.

    This is intentionally different from validating only newly
    uploaded files. Existing retained files + new uploads must
    together satisfy the active provider and organization policy.
    """
    records = list(
        records
        or []
    )

    prepared = list(
        prepared
        or []
    )


    total_count = (
        len(
            records
        )
        +
        len(
            prepared
        )
    )


    if total_count > MAX_OUTBOUND_FILES:

        raise ValueError(
            "A maximum of 10 attachments can be sent at once."
        )


    if total_count == 0:
        return


    if account is None:

        raise ValueError(
            "Select the sending mailbox before saving attachments."
        )


    limit = (
        effective_attachment_limit_bytes(
            account=account,
            user=user,
        )
    )


    total_size = sum(
        int(
            record.size
            or 0
        )
        for record
        in records
    )


    total_size += sum(
        int(
            item.get(
                "size",
                0,
            )
            or 0
        )
        for item
        in prepared
    )


    if total_size > limit:

        limit_mb = (
            limit
            /
            (
                1024
                *
                1024
            )
        )


        raise ValueError(
            "Attachments exceed the "
            f"{limit_mb:g} MB outbound limit "
            f"for {account.email_address}."
        )


def synchronize_persisted_outbound_attachments(
    *,
    message,
    retained_ids,
    prepared,
):
    """
    Apply a saved-draft attachment edit.

    Existing files explicitly retained by the client remain.
    Newly uploaded files are persisted.
    Existing files omitted from retained_ids are removed from
    both Django storage and the Attachment table.

    New files are persisted before removal of old files so an
    upload failure does not silently destroy the previous draft.
    """
    existing = list(
        message.attachments
        .all()
        .order_by(
            "id"
        )
    )


    existing_by_id = {
        record.id:
            record
        for record
        in existing
    }


    if retained_ids is None:

        retained_ids = [
            record.id
            for record
            in existing
        ]


    normalized_retained = []


    for value in retained_ids:

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


        if (
            attachment_id
            not in
            normalized_retained
        ):

            normalized_retained.append(
                attachment_id
            )


    unknown = [
        attachment_id
        for attachment_id
        in normalized_retained
        if attachment_id
        not in
        existing_by_id
    ]


    if unknown:

        raise ValueError(
            "A retained draft attachment does not belong "
            "to this draft."
        )


    retained = [
        existing_by_id[
            attachment_id
        ]
        for attachment_id
        in normalized_retained
    ]


    validate_persisted_outbound_selection(
        account=(
            message.email_account
        ),
        user=(
            message.user
        ),
        records=retained,
        prepared=prepared,
    )


    created = (
        persist_outbound_attachments(
            message=message,
            prepared=prepared,
        )
    )


    retained_set = set(
        normalized_retained
    )


    for attachment in existing:

        if (
            attachment.id
            not in
            retained_set
        ):

            _delete_attachment_record(
                attachment
            )


    final_records = [
        *retained,
        *created,
    ]


    message.attachment_meta = (
        _persistent_attachment_meta(
            final_records
        )
    )


    message.save(
        update_fields=[
            "attachment_meta"
        ]
    )


    return final_records


def move_persisted_outbound_attachments(
    *,
    source_message,
    target_message,
):
    """
    Move saved-draft files onto the resulting Sent message.

    No byte copy is required. This keeps the files durable after
    the draft row is deleted and mirrors the R1 Reply attachment
    lifecycle, where attachments remain attached to the Sent row.
    """
    records = list(
        source_message.attachments
        .all()
        .order_by(
            "id"
        )
    )


    if not records:
        return 0


    Attachment.objects.filter(
        id__in=[
            record.id
            for record
            in records
        ]
    ).update(
        message=target_message
    )


    target_message.attachment_meta = (
        _persistent_attachment_meta(
            records
        )
    )


    target_message.save(
        update_fields=[
            "attachment_meta"
        ]
    )


    source_message.attachment_meta = []


    source_message.save(
        update_fields=[
            "attachment_meta"
        ]
    )


    return len(
        records
    )
