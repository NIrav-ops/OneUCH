from django.core import signing


OAUTH_STATE_SALT = "oneuch.oauth.state.v1"
OAUTH_STATE_MAX_AGE_SECONDS = 600


class OAuthStateError(ValueError):
    pass


def create_oauth_state(*, user_id, provider):
    """
    Create a signed, timestamped OAuth state token.

    No credentials or OAuth tokens are placed in the state.
    """

    if not user_id:
        raise OAuthStateError(
            "Authenticated user is required."
        )

    if provider not in {"google", "microsoft"}:
        raise OAuthStateError(
            "Unsupported OAuth provider."
        )

    payload = {
        "user_id": int(user_id),
        "provider": provider,
    }

    return signing.dumps(
        payload,
        salt=OAUTH_STATE_SALT,
        compress=True,
    )


def resolve_oauth_state(
    *,
    state,
    provider,
    max_age=OAUTH_STATE_MAX_AGE_SECONDS,
):
    """
    Validate and decode a signed OAuth state.

    The state:
    - must be cryptographically signed
    - must be younger than max_age
    - must belong to the expected provider
    """

    if not state:
        raise OAuthStateError(
            "Missing OAuth state."
        )

    try:
        payload = signing.loads(
            state,
            salt=OAUTH_STATE_SALT,
            max_age=max_age,
        )

    except signing.SignatureExpired as exc:
        raise OAuthStateError(
            "OAuth state has expired."
        ) from exc

    except signing.BadSignature as exc:
        raise OAuthStateError(
            "Invalid OAuth state."
        ) from exc

    if not isinstance(payload, dict):
        raise OAuthStateError(
            "Invalid OAuth state payload."
        )

    if payload.get("provider") != provider:
        raise OAuthStateError(
            "OAuth provider mismatch."
        )

    user_id = payload.get("user_id")

    if not user_id:
        raise OAuthStateError(
            "OAuth state has no user identity."
        )

    try:
        user_id = int(user_id)
    except (TypeError, ValueError) as exc:
        raise OAuthStateError(
            "Invalid OAuth user identity."
        ) from exc

    return {
        "user_id": user_id,
        "provider": provider,
    }