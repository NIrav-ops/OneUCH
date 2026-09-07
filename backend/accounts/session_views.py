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
from rest_framework_simplejwt.tokens import (
    RefreshToken,
)

from accounts.authentication import (
    GENERIC_LOGIN_ERROR,
    authenticate_work_email,
)
from accounts.authentication_events import (
    record_authentication_success,
)
from accounts.browser_session import (
    BROWSER_REFRESH_COOKIE,
    BrowserSessionError,
    GENERIC_BROWSER_CSRF_ERROR,
    GENERIC_BROWSER_SESSION_ERROR,
    access_from_browser_refresh,
    browser_csrf_matches,
    browser_origin_allowed,
    browser_session_enabled,
    clear_browser_refresh_cookie,
    clear_browser_session_cookies,
    get_browser_refresh_cookie,
    new_browser_csrf_token,
    set_browser_csrf_cookie,
    set_browser_refresh_cookie,
    set_no_store,
)
from accounts.identity_service import (
    IdentityAuthenticationError,
    consume_identity_login_grant,
)
from accounts.models import (
    AUTH_METHOD_WORK_EMAIL,
)


class BrowserSessionPublicAPIView(
    APIView
):
    authentication_classes = []

    permission_classes = [
        AllowAny,
    ]

    throttle_classes = [
        ScopedRateThrottle,
    ]

    throttle_scope = (
        "browser_session"
    )

    def require_feature(
        self,
    ):
        if not (
            browser_session_enabled()
        ):
            raise NotFound()


    def csrf_failure(
        self,
    ):
        return Response(
            {
                "error":
                    GENERIC_BROWSER_CSRF_ERROR,
            },
            status=(
                status
                .HTTP_403_FORBIDDEN
            ),
        )


class BrowserSessionCsrfAPIView(
    BrowserSessionPublicAPIView
):

    def get(
        self,
        request,
    ):
        self.require_feature()

        if not (
            browser_origin_allowed(
                request
            )
        ):
            return Response(
                {
                    "error":
                        GENERIC_BROWSER_CSRF_ERROR,
                },
                status=(
                    status
                    .HTTP_403_FORBIDDEN
                ),
            )

        token = (
            new_browser_csrf_token()
        )

        response = Response(
            {
                "csrf_token":
                    token,
            }
        )

        return (
            set_browser_csrf_cookie(
                response,
                token,
            )
        )


class BrowserSessionLoginAPIView(
    BrowserSessionPublicAPIView
):

    def post(
        self,
        request,
    ):
        self.require_feature()

        if not (
            browser_csrf_matches(
                request
            )
        ):
            return self.csrf_failure()


        user = (
            authenticate_work_email(
                email=(
                    request.data.get(
                        "email"
                    )
                ),
                password=(
                    request.data.get(
                        "password"
                    )
                ),
            )
        )

        if user is None:
            return Response(
                {
                    "error":
                        GENERIC_LOGIN_ERROR,
                },
                status=(
                    status
                    .HTTP_401_UNAUTHORIZED
                ),
            )


        record_authentication_success(
            user=user,
            method=(
                AUTH_METHOD_WORK_EMAIL
            ),
        )

        refresh = (
            RefreshToken.for_user(
                user
            )
        )

        response = Response(
            {
                "access":
                    str(
                        refresh.access_token
                    ),
            }
        )

        return (
            set_browser_refresh_cookie(
                response,
                str(
                    refresh
                ),
            )
        )


class BrowserSessionIdentityExchangeAPIView(
    BrowserSessionPublicAPIView
):

    def post(
        self,
        request,
    ):
        self.require_feature()

        if not (
            browser_csrf_matches(
                request
            )
        ):
            return self.csrf_failure()


        try:
            payload = (
                consume_identity_login_grant(
                    request.data.get(
                        "code"
                    )
                )
            )

        except IdentityAuthenticationError:

            return Response(
                {
                    "error":
                        GENERIC_BROWSER_SESSION_ERROR,
                },
                status=(
                    status
                    .HTTP_401_UNAUTHORIZED
                ),
            )


        access = (
            payload.get(
                "access"
            )
        )

        refresh = (
            payload.get(
                "refresh"
            )
        )

        if (
            not access
            or
            not refresh
        ):
            return Response(
                {
                    "error":
                        GENERIC_BROWSER_SESSION_ERROR,
                },
                status=(
                    status
                    .HTTP_401_UNAUTHORIZED
                ),
            )


        response = Response(
            {
                "access":
                    access,
            }
        )

        return (
            set_browser_refresh_cookie(
                response,
                refresh,
            )
        )


class BrowserSessionEndAPIView(
    BrowserSessionPublicAPIView
):

    def post(
        self,
        request,
    ):
        self.require_feature()

        if not (
            browser_csrf_matches(
                request
            )
        ):
            return self.csrf_failure()

        response = Response(
            {
                "ended":
                    True,
            }
        )

        return (
            clear_browser_session_cookies(
                response
            )
        )


class BrowserSessionRefreshAPIView(
    BrowserSessionPublicAPIView
):

    def post(
        self,
        request,
    ):
        self.require_feature()

        if not (
            browser_csrf_matches(
                request
            )
        ):
            return self.csrf_failure()


        try:
            raw_refresh = (
                get_browser_refresh_cookie(
                    request
                )
            )

            access, _user = (
                access_from_browser_refresh(
                    raw_refresh
                )
            )

        except BrowserSessionError:

            response = Response(
                {
                    "error":
                        GENERIC_BROWSER_SESSION_ERROR,
                },
                status=(
                    status
                    .HTTP_401_UNAUTHORIZED
                ),
            )

            return (
                clear_browser_refresh_cookie(
                    response
                )
            )


        return set_no_store(
            Response(
                {
                    "access":
                        access,
                }
            )
        )


class BrowserSessionBootstrapAPIView(
    BrowserSessionPublicAPIView
):

    def post(
        self,
        request,
    ):
        self.require_feature()

        if not (
            browser_csrf_matches(
                request
            )
        ):
            return self.csrf_failure()


        try:
            raw_refresh = (
                get_browser_refresh_cookie(
                    request
                )
            )

            access, user = (
                access_from_browser_refresh(
                    raw_refresh
                )
            )

        except BrowserSessionError:

            response = Response(
                {
                    "authenticated":
                        False,
                },
                status=(
                    status
                    .HTTP_401_UNAUTHORIZED
                ),
            )

            return (
                clear_browser_refresh_cookie(
                    response
                )
            )


        return set_no_store(
            Response(
                {
                    "authenticated":
                        True,

                    "access":
                        access,

                    "user_id":
                        user.public_id,
                }
            )
        )
