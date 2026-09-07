import secrets

from django.conf import (
    settings,
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


def browser_origin_allowed(
    request,
):
    """
    The production browser-session seed must only be readable
    from an explicitly configured One UCH frontend origin.

    Local DEBUG workflows remain permissive so command-line and
    unit-test clients are not forced to synthesize browser
    Origin headers.
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
    cookie_token = str(
        request.COOKIES.get(
            BROWSER_CSRF_COOKIE
        )
        or ""
    ).strip()

    header_token = str(
        request.META.get(
            BROWSER_CSRF_HEADER_META
        )
        or ""
    ).strip()

    if (
        len(cookie_token) < 20
        or
        len(cookie_token) > 512
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


def access_from_browser_refresh(
    raw_refresh,
):
    try:
        refresh = RefreshToken(
            raw_refresh
        )

        user_id = refresh[
            api_settings
            .USER_ID_CLAIM
        ]

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

    if (
        user is None
        or
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


    return (
        str(
            refresh.access_token
        ),
        user,
    )
