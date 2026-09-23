from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async

from django.db import close_old_connections


WS_AUTH_SUBPROTOCOL = "oneuch.jwt"


def extract_websocket_access_token(
    scope,
):
    """
    Extract the One UCH access JWT from the WebSocket
    subprotocol offer.

    Browser WebSocket APIs do not support arbitrary
    Authorization headers. The fixed protocol marker is
    followed by the bearer token:

        ["oneuch.jwt", "<access-jwt>"]

    Query-string authentication is intentionally unsupported.
    """

    subprotocols = (
        scope.get(
            "subprotocols"
        )
        or []
    )

    try:
        marker_index = (
            subprotocols.index(
                WS_AUTH_SUBPROTOCOL
            )
        )
    except ValueError:
        return None

    token_index = (
        marker_index + 1
    )

    if (
        token_index
        >= len(subprotocols)
    ):
        return None

    token = (
        subprotocols[
            token_index
        ]
    )

    if (
        not isinstance(
            token,
            str,
        )
        or not token.strip()
    ):
        return None

    return token.strip()


@database_sync_to_async
def resolve_websocket_user(
    validated_token,
):
    """
    Resolve the token user through SimpleJWT's canonical
    authentication rules instead of decoding the JWT manually.
    """

    # Resolve the JWT user and then enforce the
    # same active-workspace invariant used by HTTP.
    #
    # Imports remain lazy because ASGI imports this
    # module before Django application setup completes.

    from accounts.authentication import (
        OneUCHJWTAuthentication,
        get_active_browser_session,
        get_active_membership,
    )

    authenticator = (
        OneUCHJWTAuthentication()
    )

    user = authenticator.get_user(
        validated_token
    )

    membership = (
        get_active_membership(
            user
        )
    )

    if membership is None:
        return None

    # Keep WebSocket browser-session authority aligned with
    # OneUCHJWTAuthentication.authenticate().
    #
    # Legacy/API JWTs without the browser-session claim remain
    # compatible because get_active_browser_session() returns
    # None when that claim is absent.
    #
    # Browser-session-bound JWTs fail closed when their
    # server-side BrowserSession is revoked, expired or missing.
    get_active_browser_session(
        user,
        validated_token,
    )

    return user


class JWTAuthMiddleware(
    BaseMiddleware
):

    async def __call__(
        self,
        scope,
        receive,
        send,
    ):
        close_old_connections()

        # Lazy imports remain intentional because this middleware
        # module is imported by ASGI during Django bootstrap.
        from django.contrib.auth.models import (
            AnonymousUser,
        )

        from rest_framework_simplejwt.tokens import (
            AccessToken,
        )

        from accounts.models import (
            BROWSER_SESSION_CLAIM,
        )


        scope["user"] = (
            AnonymousUser()
        )

        # Browser-session-bound sockets carry only the safe
        # server-side BrowserSession identifier in ASGI scope.
        # The bearer JWT itself is never retained in scope.
        scope["oneuch_browser_session_id"] = (
            None
        )


        token = (
            extract_websocket_access_token(
                scope
            )
        )


        if token:

            try:

                validated_token = (
                    AccessToken(
                        token
                    )
                )

                scope["user"] = (
                    await resolve_websocket_user(
                        validated_token
                    )
                )


                if (
                    scope["user"]
                    and
                    not scope["user"].is_anonymous
                ):

                    session_id = str(
                        validated_token.payload.get(
                            BROWSER_SESSION_CLAIM
                        )
                        or ""
                    ).strip()


                    if session_id:

                        scope[
                            "oneuch_browser_session_id"
                        ] = session_id


            except Exception:
                # Authentication must fail closed. Do not log
                # bearer-token material or provider payloads.
                scope["user"] = (
                    AnonymousUser()
                )


        return await super().__call__(
            scope,
            receive,
            send,
        )
