def is_ai_allowed_for_message(
    *,
    message,
    allowed_account_ids,
) -> bool:
    """
    Return True only when the message belongs to an
    explicitly approved connected email account.

    No database writes are performed.
    """

    if not allowed_account_ids:
        return False

    account_id = getattr(
        message,
        "email_account_id",
        None,
    )

    if account_id is None:
        return False

    return (
        account_id
        in allowed_account_ids
    )