from urllib.parse import (
    urlparse,
)


LOCAL_HOSTS = {
    "127.0.0.1",
    "localhost",
    "0.0.0.0",
    "::1",
}


def _is_local_hostname(
    hostname,
):
    return (
        not hostname
        or hostname.lower()
        in LOCAL_HOSTS
    )


def _validate_https_url(
    *,
    name,
    value,
    errors,
):
    parsed = urlparse(
        value or ""
    )

    if parsed.scheme != "https":
        errors.append(
            f"{name} must use HTTPS."
        )
        return

    if _is_local_hostname(
        parsed.hostname
    ):
        errors.append(
            f"{name} must not use a localhost address."
        )


def collect_pilot_configuration_errors(
    settings_obj,
):
    """
    Validate only the configuration contract required before
    One UCH is exposed to real pilot users.

    Local development is intentionally unaffected. This
    validation runs only when explicitly requested.
    """

    errors = []


    # --------------------------------------------------------
    # Django execution mode
    # --------------------------------------------------------

    if settings_obj.DEBUG:
        errors.append(
            "DEBUG must be False."
        )


    # --------------------------------------------------------
    # Secret key
    # --------------------------------------------------------

    secret_key = str(
        settings_obj.SECRET_KEY
        or ""
    )

    if (
        len(secret_key) < 32
        or "replace-" in secret_key.lower()
    ):
        errors.append(
            "DJANGO_SECRET_KEY must be a non-placeholder "
            "secret of at least 32 characters."
        )


    # --------------------------------------------------------
    # Host restriction
    # --------------------------------------------------------

    allowed_hosts = [
        str(host).strip()
        for host
        in (
            settings_obj.ALLOWED_HOSTS
            or []
        )
        if str(host).strip()
    ]

    if not allowed_hosts:
        errors.append(
            "DJANGO_ALLOWED_HOSTS must contain the "
            "public pilot backend hostname."
        )

    for host in allowed_hosts:

        normalized = (
            host.lower()
        )

        if (
            normalized == "*"
            or normalized
            in LOCAL_HOSTS
        ):
            errors.append(
                "DJANGO_ALLOWED_HOSTS must not contain "
                f"pilot-unsafe host '{host}'."
            )


    # --------------------------------------------------------
    # PostgreSQL
    # --------------------------------------------------------

    database_engine = (
        settings_obj
        .DATABASES
        .get(
            "default",
            {},
        )
        .get(
            "ENGINE",
            "",
        )
    )

    if (
        database_engine
        != "django.db.backends.postgresql"
    ):
        errors.append(
            "Pilot database engine must be PostgreSQL."
        )


    # --------------------------------------------------------
    # CORS
    # --------------------------------------------------------

    if settings_obj.CORS_ALLOW_ALL_ORIGINS:
        errors.append(
            "CORS_ALLOW_ALL_ORIGINS must be False."
        )

    cors_origins = (
        settings_obj.CORS_ALLOWED_ORIGINS
        or []
    )

    if not cors_origins:
        errors.append(
            "CORS_ALLOWED_ORIGINS must contain the "
            "public pilot frontend origin."
        )

    for origin in cors_origins:
        _validate_https_url(
            name=(
                "CORS_ALLOWED_ORIGINS entry"
            ),
            value=origin,
            errors=errors,
        )


    # --------------------------------------------------------
    # HTTPS / cookies / HSTS
    # --------------------------------------------------------

    if not settings_obj.SECURE_SSL_REDIRECT:
        errors.append(
            "SECURE_SSL_REDIRECT must be True."
        )

    if not settings_obj.SESSION_COOKIE_SECURE:
        errors.append(
            "SESSION_COOKIE_SECURE must be True."
        )

    if not settings_obj.CSRF_COOKIE_SECURE:
        errors.append(
            "CSRF_COOKIE_SECURE must be True."
        )

    if (
        settings_obj.SECURE_HSTS_SECONDS
        < 3600
    ):
        errors.append(
            "SECURE_HSTS_SECONDS must be at least 3600 "
            "for the pilot release."
        )

    if (
        settings_obj.SECURE_PROXY_SSL_HEADER
        != (
            "HTTP_X_FORWARDED_PROTO",
            "https",
        )
    ):
        errors.append(
            "SECURE_PROXY_SSL_HEADER must trust only "
            "HTTP_X_FORWARDED_PROTO=https."
        )


    # --------------------------------------------------------
    # OAuth callback transport
    # --------------------------------------------------------

    _validate_https_url(
        name="GOOGLE_REDIRECT_URI",
        value=settings_obj.GOOGLE_REDIRECT_URI,
        errors=errors,
    )

    _validate_https_url(
        name="MICROSOFT_REDIRECT_URI",
        value=settings_obj.MICROSOFT_REDIRECT_URI,
        errors=errors,
    )


    return errors
