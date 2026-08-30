def enforce_oauth_execution_policy(
    *,
    token,
    provider,
):
    """
    Fail closed before an OAuth token is used for provider
    execution or refresh.

    Connection-state projection is separate. This policy is
    authoritative for whether an existing token may actually
    be used at runtime.
    """

    provider_name = (
        str(provider or "")
        .strip()
        .lower()
    )

    if token is None:
        raise Exception(
            f"{provider_name.title()} "
            "account not connected"
        )

    if not token.is_active:
        raise Exception(
            f"{provider_name.title()} "
            "account not connected"
        )

    if token.disabled_by_admin:
        raise Exception(
            f"{provider_name.title()} "
            "access disabled by administrator"
        )

    return token
