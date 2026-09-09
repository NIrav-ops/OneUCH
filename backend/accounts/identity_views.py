
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
    IDENTITY_REGISTRATION_CONTEXT_COOKIE,
    IDENTITY_REGISTRATION_CONTEXT_COOKIE_PATH,
    IDENTITY_REGISTRATION_PURPOSE,
    IDENTITY_SIGNIN_PURPOSE,
    IdentityAuthenticationError,
    IdentityConfigurationError,
    IdentityRegistrationError,
    bind_identity_claims,
    build_authorization_url,
    build_frontend_login_redirect,
    build_registration_authorization_url,
    configured_identity_providers,
    consume_identity_login_grant,
    create_identity_login_grant,
    exchange_identity_code,
    identity_feature_enabled,
    identity_state_max_age_seconds,
    registration_feature_enabled,
    registration_public_configuration,
    resolve_identity_callback_state,
)

from accounts.registration_service import (
    RegistrationLifecycleError,
    registration_review_state_for_verified_identity,
    submit_registration_request,
)


GENERIC_PROVIDER_UNAVAILABLE = (
    "Identity provider unavailable."
)

GENERIC_GRANT_ERROR = (
    "Invalid or expired sign-in grant."
)

GENERIC_REGISTRATION_ERROR = (
    "Unable to process registration request."
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


class IdentityRegistrationConfigAPIView(
    IdentityPublicAPIView,
):

    def get(
        self,
        request,
    ):
        return Response(
            registration_public_configuration()
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


class IdentityRegistrationStartAPIView(
    IdentityPublicAPIView,
):

    def post(
        self,
        request,
        provider,
    ):
        if not (
            registration_feature_enabled()
        ):
            raise NotFound()


        organization_name = (
            request.data.get(
                "organization_name"
            )
        )

        acknowledged = (
            request.data.get(
                "acknowledged"
            )
        )


        try:

            (
                authorization_url,
                context_cookie,
                registration_config,
            ) = (
                build_registration_authorization_url(
                    provider=provider,
                    organization_name=(
                        organization_name
                    ),
                    acknowledged=(
                        acknowledged
                    ),
                )
            )


        except IdentityRegistrationError:

            return Response(
                {
                    "error":
                        GENERIC_REGISTRATION_ERROR,
                },
                status=(
                    status
                    .HTTP_400_BAD_REQUEST
                ),
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


        response = Response(
            {
                "authorization_url":
                    authorization_url,

                "provider":
                    provider,

                "privacy_notice_version":
                    registration_config[
                        "privacy_notice_version"
                    ],

                "terms_version":
                    registration_config[
                        "terms_version"
                    ],
            }
        )


        response.set_cookie(
            key=(
                IDENTITY_REGISTRATION_CONTEXT_COOKIE
            ),
            value=context_cookie,
            max_age=(
                identity_state_max_age_seconds()
            ),
            httponly=True,
            secure=(
                not settings.DEBUG
            ),
            samesite="Lax",
            path=(
                IDENTITY_REGISTRATION_CONTEXT_COOKIE_PATH
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


        signin_browser_binding = (
            request.COOKIES.get(
                IDENTITY_BROWSER_BINDING_COOKIE
            )
        )


        registration_context_cookie = (
            request.COOKIES.get(
                IDENTITY_REGISTRATION_CONTEXT_COOKIE
            )
        )


        state_value = str(
            request.GET.get(
                "state"
            )
            or ""
        ).strip()


        callback_purpose = ""

        claims = None


        try:

            transaction = (
                resolve_identity_callback_state(
                    provider=provider,
                    state=state_value,
                    signin_browser_binding=(
                        signin_browser_binding
                    ),
                    registration_context_cookie=(
                        registration_context_cookie
                    ),
                )
            )


            callback_purpose = (
                transaction[
                    "purpose"
                ]
            )


            claims = (
                exchange_identity_code(
                    provider=provider,
                    code=code,
                    nonce=(
                        transaction[
                            "nonce"
                        ]
                    ),
                )
            )


            if claims.provider != provider:

                if (
                    callback_purpose
                    ==
                    IDENTITY_REGISTRATION_PURPOSE
                ):
                    raise IdentityRegistrationError()

                raise IdentityAuthenticationError()


            if (
                callback_purpose
                ==
                IDENTITY_REGISTRATION_PURPOSE
            ):

                context = (
                    transaction[
                        "registration"
                    ]
                )


                (
                    registration,
                    created,
                ) = (
                    submit_registration_request(
                        provider=(
                            claims.provider
                        ),
                        issuer=(
                            claims.issuer
                        ),
                        subject=(
                            claims.subject
                        ),
                        email=(
                            claims.email
                        ),
                        organization_name=(
                            context[
                                "organization_name"
                            ]
                        ),
                        privacy_notice_version=(
                            context[
                                "privacy_notice_version"
                            ]
                        ),
                        terms_version=(
                            context[
                                "terms_version"
                            ]
                        ),
                        consent_recorded_at=(
                            context[
                                "consent_recorded_at"
                            ]
                        ),
                        requested_region=(
                            context[
                                "requested_region"
                            ]
                        ),
                    )
                )


                target = (
                    build_frontend_login_redirect(
                        registration_status=(
                            registration.status
                        ),
                        registration_id=(
                            registration.public_id
                        ),
                        registration_created=(
                            "1"
                            if created
                            else "0"
                        ),
                        identity_provider=provider,
                    )
                )


            elif (
                callback_purpose
                ==
                IDENTITY_SIGNIN_PURPOSE
            ):

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


            else:

                raise IdentityAuthenticationError()


        except IdentityConfigurationError:

            target = (
                build_frontend_login_redirect(
                    identity_error=(
                        "provider_unavailable"
                    ),
                    identity_provider=provider,
                )
            )


        except (
            IdentityRegistrationError,
            RegistrationLifecycleError,
        ):

            target = (
                build_frontend_login_redirect(
                    registration_error=(
                        "registration_failed"
                    ),
                    identity_provider=provider,
                )
            )


        except IdentityAuthenticationError:

            if (
                callback_purpose
                ==
                IDENTITY_REGISTRATION_PURPOSE
            ):

                target = (
                    build_frontend_login_redirect(
                        registration_error=(
                            "registration_failed"
                        ),
                        identity_provider=provider,
                    )
                )


            else:

                registration_state = None


                if claims is not None:

                    registration_state = (
                        registration_review_state_for_verified_identity(
                            provider=(
                                claims.provider
                            ),
                            issuer=(
                                claims.issuer
                            ),
                            subject=(
                                claims.subject
                            ),
                        )
                    )


                if registration_state:

                    target = (
                        build_frontend_login_redirect(
                            registration_status=(
                                registration_state[
                                    "status"
                                ]
                            ),
                            registration_id=(
                                registration_state[
                                    "registration_id"
                                ]
                            ),
                            registration_created="0",
                            identity_provider=provider,
                        )
                    )


                else:

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


        response.delete_cookie(
            key=(
                IDENTITY_REGISTRATION_CONTEXT_COOKIE
            ),
            path=(
                IDENTITY_REGISTRATION_CONTEXT_COOKIE_PATH
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
