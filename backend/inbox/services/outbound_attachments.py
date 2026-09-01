from pathlib import PurePath


MEBIBYTE = (
    1024
    *
    1024
)

MAX_OUTBOUND_FILES = 10

GMAIL_RAW_LIMIT_BYTES = (
    18
    *
    MEBIBYTE
)

OUTLOOK_SIMPLE_LIMIT_BYTES = (
    3
    *
    MEBIBYTE
)


def _provider_limit_bytes(
    account,
):
    if (
        account.account_type
        ==
        "gmail"
    ):
        return (
            GMAIL_RAW_LIMIT_BYTES
        )

    if (
        account.account_type
        ==
        "outlook"
    ):
        return (
            OUTLOOK_SIMPLE_LIMIT_BYTES
        )

    raise ValueError(
        "Unsupported email account type"
    )


def _organization_limit_bytes(
    *,
    user,
):
    membership = getattr(
        user,
        "organization_membership",
        None,
    )

    organization = (
        membership.organization
        if membership
        else None
    )

    policy = (
        getattr(
            organization,
            "attachment_policy",
            None,
        )
        if organization
        else None
    )

    if (
        policy is None
        or
        not getattr(
            policy,
            "max_size_mb",
            None,
        )
    ):
        return None

    return (
        int(
            policy.max_size_mb
        )
        *
        MEBIBYTE
    )


def effective_attachment_limit_bytes(
    *,
    account,
    user,
):
    provider_limit = (
        _provider_limit_bytes(
            account
        )
    )

    organization_limit = (
        _organization_limit_bytes(
            user=user
        )
    )

    if organization_limit is None:
        return provider_limit

    return min(
        provider_limit,
        organization_limit,
    )


def prepare_outbound_attachments(
    *,
    request,
    account,
):
    """
    Read and validate user-uploaded outbound files.

    No file is persisted by this helper. It is intentionally
    for immediate provider delivery only.
    """
    files = []

    request_files = getattr(
        request,
        "FILES",
        None,
    )

    if request_files:
        files = list(
            request_files.getlist(
                "attachments"
            )
        )


    if not files:
        return []


    if (
        len(
            files
        )
        >
        MAX_OUTBOUND_FILES
    ):
        raise ValueError(
            "A maximum of 10 attachments can be sent at once."
        )


    limit = (
        effective_attachment_limit_bytes(
            account=account,
            user=request.user,
        )
    )


    total = 0

    prepared = []


    for upload in files:

        filename = (
            PurePath(
                str(
                    upload.name
                    or ""
                )
            )
            .name
            .strip()
        )


        if not filename:
            raise ValueError(
                "Every attachment must have a filename."
            )


        content = (
            upload.read()
        )


        size = len(
            content
        )


        if size <= 0:
            raise ValueError(
                f"{filename} is empty."
            )


        total += size


        if total > limit:

            limit_mb = (
                limit
                /
                MEBIBYTE
            )

            raise ValueError(
                "Attachments exceed the "
                f"{limit_mb:g} MB outbound limit "
                f"for {account.email_address}."
            )


        content_type = (
            str(
                getattr(
                    upload,
                    "content_type",
                    "",
                )
                or
                "application/octet-stream"
            )
            .strip()
        )


        prepared.append(
            {
                "filename":
                    filename,

                "content_type":
                    content_type,

                "size":
                    size,

                "content":
                    content,
            }
        )


    return prepared


def attachment_metadata(
    prepared,
):
    """
    Local sent-message metadata.

    attachment_id stays absent until provider synchronization
    supplies a provider-native downloadable attachment ID.
    """
    return [
        {
            "filename":
                item[
                    "filename"
                ],

            "mime_type":
                item[
                    "content_type"
                ],

            "size":
                item[
                    "size"
                ],

            "attachment_id":
                None,

            "outbound":
                True,
        }

        for item
        in (
            prepared
            or []
        )
    ]
