def is_ai_allowed_for_message(
    *,
    message,
    allowed_account_ids,
) -> bool:
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
