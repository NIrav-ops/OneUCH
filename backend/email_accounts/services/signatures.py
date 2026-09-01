def normalized_signature_text(
    account,
):
    return (
        str(
            getattr(
                account,
                "signature_text",
                "",
            )
            or ""
        )
        .strip()
    )


def apply_account_signature(
    *,
    account,
    body,
):
    """
    Append the One UCH-managed mailbox signature exactly once.

    This function is deterministic and provider-independent.
    Provider client settings are never assumed.

    The stored user-authored body remains first, followed by
    the mailbox signature.
    """
    value = (
        str(
            body
            or ""
        )
        .rstrip()
    )


    if not getattr(
        account,
        "signature_enabled",
        False,
    ):
        return value


    signature = (
        normalized_signature_text(
            account
        )
    )


    if not signature:
        return value


    # Retry / internal delegation safety.
    if (
        value == signature
        or
        value.endswith(
            "\n\n"
            + signature
        )
    ):
        return value


    if not value:
        return signature


    return (
        value
        +
        "\n\n"
        +
        signature
    )
