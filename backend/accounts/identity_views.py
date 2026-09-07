
from django.conf import (
    settings,
)
from django.shortcuts import (
    redirect,
)

from rest_framework import (
    status,
)
from rest_framework.exceptions import (
    NotFound,
)
from rest_framework.permissions import (
    AllowAny,
)
from rest_framework.response import (
    Response,
)
from rest_framework.throttling import (
    ScopedRateThrottle,
)
from rest_framework.views import (
    APIView,
)

from accounts.identity_service import (
    IDENTITY_BROWSER_BINDING_COOKIE,
    IDENTITY_BROWSER_BINDING_COOKIE_PATH,
    IdentityAuthenticationError,
    IdentityConfigurationError,
    bind_identity_claims,
    build_authorization_url,
    build_frontend_login_redirect,
    configured_identity_providers,
    consume_identity_login_grant,
    create_identity_login_grant,
    exchange_identity_code,
    identity_feature_enabled,
    identity_state_max_age_seconds,
    resolve_identity_state,
)


GENERIC_PROVIDER_UNAVAILABLE = (
    "Identity provider unavailable."
)

GENERIC_GRANT_ERROR = (
    "Invalid or expired sign-in grant."
)


class IdentityPublicAPIView(
    APIView,
):
    authentication_classes = []

    permission_classes = [
        AllowAny,
    ]

    throttle_classes = [
        ScopedRateThrottle,
    ]

    throttle_scope = (
        "identity_login"
    )


class IdentityProvidersAPIView(
    IdentityPublicAPIView,
):

    def get(
        self,
        request,
    ):
        enabled = (
            identity_feature_enabled()
        )

        providers = (
            configured_identity_providers()
            if enabled
            else []
        )

        return Response(
            {
                "enabled":
                    enabled,

                "providers":
                    providers,
            }
        )


class IdentityStartAPIView(
    IdentityPublicAPIView,
):

    def get(
        self,
        request,
        provider,
    ):
        if not (
            identity_feature_enabled()
        ):
            raise NotFound()

        try:
            (
                authorization_url,
                browser_binding,
            ) = build_authorization_url(
                provider
            )

        except IdentityConfigurationError:

            return Response(
                {
                    "error":
                        GENERIC_PROVIDER_UNAVAILABLE,
                },
                status=(
                    status
                    .HTTP_503_SERVICE_UNAVAILABLE
                ),
            )

        response = redirect(
            authorization_url
        )

        response.set_cookie(
            key=(
                IDENTITY_BROWSER_BINDING_COOKIE
            ),
            value=browser_binding,
            max_age=(
                identity_state_max_age_seconds()
            ),
            httponly=True,
            secure=(
                not settings.DEBUG
            ),
            samesite="Lax",
            path=(
                IDENTITY_BROWSER_BINDING_COOKIE_PATH
            ),
        )

        response[
            "Cache-Control"
        ] = "no-store"

        return response


class IdentityCallbackAPIView(
    IdentityPublicAPIView,
):

    def get(
        self,
        request,
        provider,
    ):
        if not (
            identity_feature_enabled()
        ):
            raise NotFound()

        code = str(
            request.GET.get(
                "code"
            )
            or ""
        ).strip()

        browser_binding = (
            request.COOKIES.get(
                IDENTITY_BROWSER_BINDING_COOKIE
            )
        )

        state_value = str(
            request.GET.get(
                "state"
            )
            or ""
        ).strip()

        try:
            nonce = (
                resolve_identity_state(
                    provider=provider,
                    state=state_value,
                    browser_binding=(
                        browser_binding
                    ),
                )
            )

            claims = (
                exchange_identity_code(
                    provider=provider,
                    code=code,
                    nonce=nonce,
                )
            )

            if claims.provider != provider:
                raise IdentityAuthenticationError()

            user = (
                bind_identity_claims(
                    claims
                )
            )

            grant = (
                create_identity_login_grant(
                    user=user,
                    provider=provider,
                )
            )

            target = (
                build_frontend_login_redirect(
                    identity_code=grant,
                    identity_provider=provider,
                )
            )

        except IdentityConfigurationError:

            target = (
                build_frontend_login_redirect(
                    identity_error=(
                        "provider_unavailable"
                    ),
                    identity_provider=provider,
                )
            )

        except IdentityAuthenticationError:

            target = (
                build_frontend_login_redirect(
                    identity_error=(
                        "signin_failed"
                    ),
                    identity_provider=provider,
                )
            )

        response = redirect(
            target
        )

        response.delete_cookie(
            key=(
                IDENTITY_BROWSER_BINDING_COOKIE
            ),
            path=(
                IDENTITY_BROWSER_BINDING_COOKIE_PATH
            ),
            samesite="Lax",
        )

        response[
            "Cache-Control"
        ] = "no-store"

        return response


class IdentityExchangeAPIView(
    IdentityPublicAPIView,
):

    def post(
        self,
        request,
    ):
        if not (
            identity_feature_enabled()
        ):
            raise NotFound()

        grant = (
            request.data.get(
                "code"
            )
        )

        try:
            payload = (
                consume_identity_login_grant(
                    grant
                )
            )

        except IdentityAuthenticationError:

            return Response(
                {
                    "error":
                        GENERIC_GRANT_ERROR,
                },
                status=(
                    status
                    .HTTP_401_UNAUTHORIZED
                ),
            )

        return Response(
            payload
        )
