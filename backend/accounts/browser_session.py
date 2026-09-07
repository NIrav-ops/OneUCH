from datetime import (
    UTC,
    datetime,
)
import secrets

from django.conf import (
    settings,
)
from django.core.exceptions import (
    ValidationError,
)
from django.db import (
    transaction,
)
from django.utils import (
    timezone,
)

from rest_framework_simplejwt.exceptions import (
    TokenError,
)
from rest_framework_simplejwt.settings import (
    api_settings,
)
from rest_framework_simplejwt.tokens import (
    RefreshToken,
)

from accounts.authentication import (
    get_active_membership,
)
from accounts.models import (
    BROWSER_SESSION_CLAIM,
    BrowserSession,
    User,
)


BROWSER_REFRESH_COOKIE = (
    "oneuch_refresh"
)

BROWSER_CSRF_COOKIE = (
    "oneuch_session_csrf"
)

BROWSER_SESSION_COOKIE_PATH = (
    "/api/auth/session/"
)

BROWSER_CSRF_HEADER_META = (
    "HTTP_X_ONEUCH_CSRF"
)

GENERIC_BROWSER_SESSION_ERROR = (
    "Browser session is unavailable."
)

GENERIC_BROWSER_CSRF_ERROR = (
    "Session verification failed."
)


class BrowserSessionError(
    Exception
):
    pass


class BrowserSessionReuseError(
    BrowserSessionError
):
    pass


def browser_session_enabled():
    return bool(
        getattr(
            settings,
            "AUTH_BROWSER_SESSION_ENABLED",
            False,
        )
    )


def browser_cookie_secure():
    return not settings.DEBUG


def browser_cookie_max_age_seconds():
    lifetime = (
        settings
        .SIMPLE_JWT[
            "REFRESH_TOKEN_LIFETIME"
        ]
    )

    return int(
        lifetime.total_seconds()
    )


def new_browser_csrf_token():
    return secrets.token_urlsafe(
        32
    )


def get_browser_csrf_cookie(
    request,
):
    value = str(
        request.COOKIES.get(
            BROWSER_CSRF_COOKIE
        )
        or ""
    ).strip()

    if (
        len(value) < 20
        or
        len(value) > 512
    ):
        return None

    return value


def browser_origin_allowed(
    request,
):
    """
    Production CSRF seed access remains bound to an explicitly
    configured One UCH frontend origin.

    DEBUG keeps the existing local/test behavior.
    """

    if settings.DEBUG:
        return True

    origin = str(
        request.headers.get(
            "Origin"
        )
        or ""
    ).strip().rstrip(
        "/"
    )

    if not origin:
        return False

    allowed = {
        str(value)
        .strip()
        .rstrip("/")

        for value
        in (
            settings
            .CORS_ALLOWED_ORIGINS
            or []
        )

        if str(value).strip()
    }

    return (
        origin
        in allowed
    )


def browser_csrf_matches(
    request,
):
    cookie_token = (
        get_browser_csrf_cookie(
            request
        )
    )

    header_token = str(
        request.META.get(
            BROWSER_CSRF_HEADER_META
        )
        or ""
    ).strip()

    if (
        cookie_token is None
        or
        len(header_token) < 20
        or
        len(header_token) > 512
    ):
        return False

    return secrets.compare_digest(
        cookie_token,
        header_token,
    )


def set_no_store(
    response,
):
    response[
        "Cache-Control"
    ] = "no-store"

    response[
        "Pragma"
    ] = "no-cache"

    return response


def set_browser_csrf_cookie(
    response,
    token,
):
    response.set_cookie(
        key=BROWSER_CSRF_COOKIE,
        value=token,
        max_age=(
            browser_cookie_max_age_seconds()
        ),
        httponly=True,
        secure=browser_cookie_secure(),
        samesite="Lax",
        path=(
            BROWSER_SESSION_COOKIE_PATH
        ),
    )

    return set_no_store(
        response
    )


def set_browser_refresh_cookie(
    response,
    refresh_token,
):
    response.set_cookie(
        key=BROWSER_REFRESH_COOKIE,
        value=str(
            refresh_token
        ),
        max_age=(
            browser_cookie_max_age_seconds()
        ),
        httponly=True,
        secure=browser_cookie_secure(),
        samesite="Lax",
        path=(
            BROWSER_SESSION_COOKIE_PATH
        ),
    )

    return set_no_store(
        response
    )


def clear_browser_refresh_cookie(
    response,
):
    response.delete_cookie(
        key=BROWSER_REFRESH_COOKIE,
        path=(
            BROWSER_SESSION_COOKIE_PATH
        ),
        samesite="Lax",
    )

    return set_no_store(
        response
    )


def clear_browser_csrf_cookie(
    response,
):
    response.delete_cookie(
        key=BROWSER_CSRF_COOKIE,
        path=(
            BROWSER_SESSION_COOKIE_PATH
        ),
        samesite="Lax",
    )

    return set_no_store(
        response
    )


def clear_browser_session_cookies(
    response,
):
    clear_browser_refresh_cookie(
        response
    )

    clear_browser_csrf_cookie(
        response
    )

    return set_no_store(
        response
    )


def get_browser_refresh_cookie(
    request,
):
    value = str(
        request.COOKIES.get(
            BROWSER_REFRESH_COOKIE
        )
        or ""
    ).strip()

    if (
        len(value) < 20
        or
        len(value) > 4096
    ):
        raise BrowserSessionError(
            GENERIC_BROWSER_SESSION_ERROR
        )

    return value


def _refresh_expiry(
    refresh,
):
    try:
        return datetime.fromtimestamp(
            int(
                refresh[
                    "exp"
                ]
            ),
            tz=UTC,
        )

    except (
        KeyError,
        TypeError,
        ValueError,
        OSError,
        OverflowError,
    ) as exc:

        raise BrowserSessionError(
            GENERIC_BROWSER_SESSION_ERROR
        ) from exc


def _parse_refresh(
    raw_refresh,
):
    raw_refresh = str(
        raw_refresh
        or ""
    ).strip()

    if (
        len(raw_refresh) < 20
        or
        len(raw_refresh) > 4096
    ):
        raise BrowserSessionError(
            GENERIC_BROWSER_SESSION_ERROR
        )

    try:
        refresh = RefreshToken(
            raw_refresh
        )

        user_id = refresh[
            api_settings
            .USER_ID_CLAIM
        ]

        jti = str(
            refresh[
                api_settings
                .JTI_CLAIM
            ]
        )

    except (
        KeyError,
        TokenError,
        TypeError,
        ValueError,
    ) as exc:

        raise BrowserSessionError(
            GENERIC_BROWSER_SESSION_ERROR
        ) from exc


    user_filter = {
        api_settings.USER_ID_FIELD:
            user_id,
    }

    user = (
        User.objects
        .filter(
            **user_filter
        )
        .first()
    )

    if user is None:
        raise BrowserSessionError(
            GENERIC_BROWSER_SESSION_ERROR
        )


    return (
        refresh,
        user,
        jti,
    )


def _assert_session_eligible_user(
    user,
):
    if (
        not user.is_active
        or
        get_active_membership(
            user
        )
        is None
    ):
        raise BrowserSessionError(
            GENERIC_BROWSER_SESSION_ERROR
        )


def _bind_refresh_to_new_browser_session(
    refresh,
    user,
    jti,
):
    _assert_session_eligible_user(
        user
    )

    session = (
        BrowserSession.objects.create(
            user=user,
            current_refresh_jti=jti,
            expires_at=(
                _refresh_expiry(
                    refresh
                )
            ),
        )
    )

    refresh[
        BROWSER_SESSION_CLAIM
    ] = str(
        session.public_id
    )

    return (
        str(
            refresh.access_token
        ),
        str(
            refresh
        ),
        user,
        session,
    )


def create_browser_session_tokens(
    user,
):
    _assert_session_eligible_user(
        user
    )

    refresh = (
        RefreshToken.for_user(
            user
        )
    )

    jti = str(
        refresh[
            api_settings
            .JTI_CLAIM
        ]
    )

    return (
        _bind_refresh_to_new_browser_session(
            refresh,
            user,
            jti,
        )
    )


def create_browser_session_from_refresh(
    raw_refresh,
):
    refresh, user, jti = (
        _parse_refresh(
            raw_refresh
        )
    )

    return (
        _bind_refresh_to_new_browser_session(
            refresh,
            user,
            jti,
        )
    )


def _session_for_refresh(
    refresh,
    user,
):
    session_id = str(
        refresh.payload.get(
            BROWSER_SESSION_CLAIM
        )
        or ""
    ).strip()

    if not session_id:
        raise BrowserSessionError(
            GENERIC_BROWSER_SESSION_ERROR
        )

    try:
        session = (
            BrowserSession.objects
            .select_for_update()
            .filter(
                public_id=session_id,
                user=user,
            )
            .first()
        )

    except (
        ValidationError,
        TypeError,
        ValueError,
    ) as exc:

        raise BrowserSessionError(
            GENERIC_BROWSER_SESSION_ERROR
        ) from exc


    if session is None:
        raise BrowserSessionError(
            GENERIC_BROWSER_SESSION_ERROR
        )


    return session


def _revoke_session(
    session,
    *,
    reason,
    now=None,
):
    if (
        session.revoked_at
        is not None
    ):
        return session

    now = (
        now
        or
        timezone.now()
    )

    session.revoked_at = (
        now
    )

    session.revocation_reason = (
        str(
            reason
            or "revoked"
        )[:40]
    )

    session.save(
        update_fields=[
            "revoked_at",
            "revocation_reason",
        ]
    )

    return session


def rotate_browser_refresh(
    raw_refresh,
):
    refresh, user, presented_jti = (
        _parse_refresh(
            raw_refresh
        )
    )

    deferred_error = None
    result = None


    with transaction.atomic():

        session = (
            _session_for_refresh(
                refresh,
                user,
            )
        )

        now = timezone.now()


        if (
            session.revoked_at
            is not None
            or
            session.expires_at
            <= now
        ):
            raise BrowserSessionError(
                GENERIC_BROWSER_SESSION_ERROR
            )


        if (
            presented_jti
            !=
            session.current_refresh_jti
        ):

            _revoke_session(
                session,
                reason="refresh_reuse",
                now=now,
            )

            # Deliberately leave the atomic block normally.
            # Raising inside it would roll back the server
            # revocation that protects the whole session.

            deferred_error = (
                BrowserSessionReuseError(
                    GENERIC_BROWSER_SESSION_ERROR
                )
            )


        elif not user.is_active:

            _revoke_session(
                session,
                reason="user_inactive",
                now=now,
            )

            deferred_error = (
                BrowserSessionError(
                    GENERIC_BROWSER_SESSION_ERROR
                )
            )


        elif (
            get_active_membership(
                user
            )
            is None
        ):

            _revoke_session(
                session,
                reason="workspace_inactive",
                now=now,
            )

            deferred_error = (
                BrowserSessionError(
                    GENERIC_BROWSER_SESSION_ERROR
                )
            )


        else:

            replacement = (
                RefreshToken.for_user(
                    user
                )
            )

            replacement[
                BROWSER_SESSION_CLAIM
            ] = str(
                session.public_id
            )


            # Rotation must not produce an indefinite
            # sliding browser session.

            replacement[
                "exp"
            ] = int(
                session.expires_at
                .timestamp()
            )


            session.current_refresh_jti = (
                str(
                    replacement[
                        api_settings
                        .JTI_CLAIM
                    ]
                )
            )

            session.last_rotated_at = (
                now
            )

            session.save(
                update_fields=[
                    "current_refresh_jti",
                    "last_rotated_at",
                ]
            )


            result = (
                str(
                    replacement.access_token
                ),
                str(
                    replacement
                ),
                user,
                session,
            )


    # Any security revocation above has now committed.
    # Reject the triggering credential only after the
    # transaction has closed successfully.

    if deferred_error is not None:
        raise deferred_error


    if result is None:
        raise BrowserSessionError(
            GENERIC_BROWSER_SESSION_ERROR
        )


    return result


@transaction.atomic
def revoke_browser_session(
    raw_refresh,
    *,
    reason="logout",
):
    refresh, user, _presented_jti = (
        _parse_refresh(
            raw_refresh
        )
    )

    session = (
        _session_for_refresh(
            refresh,
            user,
        )
    )

    return (
        _revoke_session(
            session,
            reason=reason,
        )
    )
