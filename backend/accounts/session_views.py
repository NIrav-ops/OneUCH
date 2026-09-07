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

from accounts.authentication import (
    GENERIC_LOGIN_ERROR,
    authenticate_work_email,
)
from accounts.authentication_events import (
    record_authentication_success,
)
from accounts.browser_session import (
    BrowserSessionError,
    GENERIC_BROWSER_CSRF_ERROR,
    GENERIC_BROWSER_SESSION_ERROR,
    browser_csrf_matches,
    browser_origin_allowed,
    browser_session_enabled,
    clear_browser_refresh_cookie,
    clear_browser_session_cookies,
    create_browser_session_from_refresh,
    create_browser_session_tokens,
    get_browser_csrf_cookie,
    get_browser_refresh_cookie,
    new_browser_csrf_token,
    revoke_browser_session,
    rotate_browser_refresh,
    set_browser_csrf_cookie,
    set_browser_refresh_cookie,
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


        # Reuse an existing valid cookie so a second tab does
        # not invalidate the first tab's in-memory CSRF proof.

        token = (
            get_browser_csrf_cookie(
                request
            )
            or
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


        try:
            (
                access,
                refresh,
                _user,
                _session,
            ) = (
                create_browser_session_tokens(
                    user
                )
            )

        except BrowserSessionError:

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


        raw_refresh = (
            payload.get(
                "refresh"
            )
        )

        if (
            not payload.get(
                "access"
            )
            or
            not raw_refresh
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


        try:
            (
                access,
                refresh,
                _user,
                _session,
            ) = (
                create_browser_session_from_refresh(
                    raw_refresh
                )
            )

        except BrowserSessionError:

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


        # Logout is idempotent from the browser's perspective.
        # When a valid bound refresh credential is present,
        # revoke its entire server browser session first.

        try:
            raw_refresh = (
                get_browser_refresh_cookie(
                    request
                )
            )

            revoke_browser_session(
                raw_refresh,
                reason="logout",
            )

        except BrowserSessionError:
            pass


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

            (
                access,
                refresh,
                _user,
                _session,
            ) = (
                rotate_browser_refresh(
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

            (
                access,
                refresh,
                user,
                _session,
            ) = (
                rotate_browser_refresh(
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


        response = Response(
            {
                "authenticated":
                    True,

                "access":
                    access,

                "user_id":
                    user.public_id,
            }
        )

        return (
            set_browser_refresh_cookie(
                response,
                refresh,
            )
        )
