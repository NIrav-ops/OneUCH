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


def _is_placeholder_value(
    value,
):
    normalized = str(
        value
        or ""
    ).strip().lower()

    return (
        not normalized
        or
        normalized == "replace-me"
        or
        normalized.startswith(
            "replace-with-"
        )
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


    # --------------------------------------------------------
    # Identity-only Sign-In
    # --------------------------------------------------------
    #
    # Identity remains optional/fail-closed for pilot
    # deployments. Once explicitly enabled, all identity
    # provider configuration must be production-safe.
    # --------------------------------------------------------

    identity_enabled = bool(
        getattr(
            settings_obj,
            "AUTH_IDENTITY_SIGNIN_ENABLED",
            False,
        )
    )

    if identity_enabled:

        required_identity_values = (
            (
                "GOOGLE_IDENTITY_CLIENT_ID",
                getattr(
                    settings_obj,
                    "GOOGLE_IDENTITY_CLIENT_ID",
                    "",
                ),
            ),
            (
                "GOOGLE_IDENTITY_CLIENT_SECRET",
                getattr(
                    settings_obj,
                    "GOOGLE_IDENTITY_CLIENT_SECRET",
                    "",
                ),
            ),
            (
                "MICROSOFT_IDENTITY_CLIENT_ID",
                getattr(
                    settings_obj,
                    "MICROSOFT_IDENTITY_CLIENT_ID",
                    "",
                ),
            ),
            (
                "MICROSOFT_IDENTITY_CLIENT_SECRET",
                getattr(
                    settings_obj,
                    "MICROSOFT_IDENTITY_CLIENT_SECRET",
                    "",
                ),
            ),
        )

        for (
            setting_name,
            setting_value,
        ) in required_identity_values:

            if _is_placeholder_value(
                setting_value
            ):
                errors.append(
                    f"{setting_name} must be configured with a "
                    "non-placeholder value when identity sign-in "
                    "is enabled."
                )


        frontend_login_url = getattr(
            settings_obj,
            "ONEUCH_FRONTEND_LOGIN_URL",
            "",
        )

        google_identity_redirect = getattr(
            settings_obj,
            "GOOGLE_IDENTITY_REDIRECT_URI",
            "",
        )

        microsoft_identity_redirect = getattr(
            settings_obj,
            "MICROSOFT_IDENTITY_REDIRECT_URI",
            "",
        )


        _validate_https_url(
            name="ONEUCH_FRONTEND_LOGIN_URL",
            value=frontend_login_url,
            errors=errors,
        )

        _validate_https_url(
            name="GOOGLE_IDENTITY_REDIRECT_URI",
            value=google_identity_redirect,
            errors=errors,
        )

        _validate_https_url(
            name="MICROSOFT_IDENTITY_REDIRECT_URI",
            value=microsoft_identity_redirect,
            errors=errors,
        )


        # The one-time identity login grant must return only
        # to an explicitly allowed One UCH frontend origin.

        frontend_parsed = urlparse(
            frontend_login_url
            or ""
        )

        if (
            frontend_parsed.scheme == "https"
            and
            frontend_parsed.netloc
            and
            not _is_local_hostname(
                frontend_parsed.hostname
            )
        ):
            frontend_origin = (
                f"{frontend_parsed.scheme}://"
                f"{frontend_parsed.netloc}"
            ).rstrip(
                "/"
            )

            allowed_frontend_origins = {
                str(origin)
                .strip()
                .rstrip("/")

                for origin
                in cors_origins

                if str(origin).strip()
            }

            if (
                frontend_origin
                not in allowed_frontend_origins
            ):
                errors.append(
                    "ONEUCH_FRONTEND_LOGIN_URL origin must be "
                    "present in CORS_ALLOWED_ORIGINS."
                )


        # Both identity callbacks must return to the One UCH
        # backend host actually allowed by Django.

        safe_backend_hosts = {
            str(host)
            .strip()
            .lower()

            for host
            in allowed_hosts

            if (
                str(host).strip()
                and
                str(host).strip() != "*"
                and
                str(host).strip().lower()
                not in LOCAL_HOSTS
            )
        }

        for (
            setting_name,
            callback_url,
        ) in (
            (
                "GOOGLE_IDENTITY_REDIRECT_URI",
                google_identity_redirect,
            ),
            (
                "MICROSOFT_IDENTITY_REDIRECT_URI",
                microsoft_identity_redirect,
            ),
        ):
            parsed_callback = urlparse(
                callback_url
                or ""
            )

            callback_hostname = (
                parsed_callback.hostname
                or ""
            ).lower()

            if (
                parsed_callback.scheme == "https"
                and
                callback_hostname
                and
                callback_hostname
                not in LOCAL_HOSTS
                and
                callback_hostname
                not in safe_backend_hosts
            ):
                errors.append(
                    f"{setting_name} hostname must be present "
                    "in DJANGO_ALLOWED_HOSTS."
                )


        # Maintain the E2 architectural boundary: identity
        # Sign-In and mailbox authorization use separate OAuth
        # applications.

        google_identity_client = str(
            getattr(
                settings_obj,
                "GOOGLE_IDENTITY_CLIENT_ID",
                "",
            )
            or ""
        ).strip()

        google_mailbox_client = str(
            getattr(
                settings_obj,
                "GOOGLE_CLIENT_ID",
                "",
            )
            or ""
        ).strip()

        if (
            google_identity_client
            and
            google_mailbox_client
            and
            not _is_placeholder_value(
                google_identity_client
            )
            and
            google_identity_client
            == google_mailbox_client
        ):
            errors.append(
                "GOOGLE_IDENTITY_CLIENT_ID must use a separate "
                "OAuth client from GOOGLE_CLIENT_ID."
            )


        microsoft_identity_client = str(
            getattr(
                settings_obj,
                "MICROSOFT_IDENTITY_CLIENT_ID",
                "",
            )
            or ""
        ).strip()

        microsoft_mailbox_client = str(
            getattr(
                settings_obj,
                "MICROSOFT_CLIENT_ID",
                "",
            )
            or ""
        ).strip()

        if (
            microsoft_identity_client
            and
            microsoft_mailbox_client
            and
            not _is_placeholder_value(
                microsoft_identity_client
            )
            and
            microsoft_identity_client
            == microsoft_mailbox_client
        ):
            errors.append(
                "MICROSOFT_IDENTITY_CLIENT_ID must use a "
                "separate OAuth client from "
                "MICROSOFT_CLIENT_ID."
            )


    return errors
