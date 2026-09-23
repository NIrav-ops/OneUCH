import json

from channels.db import (
    database_sync_to_async,
)

from channels.generic.websocket import (
    AsyncWebsocketConsumer,
)

from django.core.exceptions import (
    ValidationError,
)

from django.utils import (
    timezone,
)

from authentication.jwt_ws_middleware import (
    WS_AUTH_SUBPROTOCOL,
)


@database_sync_to_async
def browser_session_authority_is_active(
    *,
    user,
    session_id,
):
    """
    Revalidate server-side browser-session authority at the
    realtime delivery boundary.

    Legacy/API JWT sockets have no browser-session claim and
    retain the historical authentication contract.

    Browser-session-bound sockets fail closed after logout,
    reuse revocation, expiry or session removal.
    """

    if not session_id:
        return True


    from accounts.models import (
        BrowserSession,
    )


    try:

        return (
            BrowserSession.objects
            .filter(
                public_id=session_id,
                user=user,
                revoked_at__isnull=True,
                expires_at__gt=(
                    timezone.now()
                ),
            )
            .exists()
        )


    except (
        ValidationError,
        TypeError,
        ValueError,
    ):

        return False



class InboxConsumer(AsyncWebsocketConsumer):

    async def connect(self):

        # Get user from websocket scope
        user = self.scope.get("user")

        # If user is not authenticated, reject
        if not user or user.is_anonymous:
            await self.close(
                code=4401
            )
            return

        # Save user
        self.user = user

        # Create user specific group
        self.group_name = f"inbox_{self.user.id}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept(
            subprotocol=WS_AUTH_SUBPROTOCOL
        )

        print("WebSocket CONNECTED:", self.group_name)


    async def disconnect(self, close_code):

        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

        print("WebSocket DISCONNECTED")


    async def _realtime_authority_active(self):

        return await (
            browser_session_authority_is_active(
                user=self.user,
                session_id=(
                    self.scope.get(
                        "oneuch_browser_session_id"
                    )
                ),
            )
        )


    async def _close_if_realtime_authority_revoked(
        self,
    ):

        if await self._realtime_authority_active():
            return False


        if hasattr(
            self,
            "group_name",
        ):

            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name,
            )


        await self.close(
            code=4401
        )

        return True


    async def inbox_update(self, event):

        if await (
            self._close_if_realtime_authority_revoked()
        ):
            return


        await self.send(
            text_data=json.dumps(event["data"])
        )


    async def send_update(self, event):

        if await (
            self._close_if_realtime_authority_revoked()
        ):
            return


        await self.send(
            text_data=json.dumps({
                "type": "update"
            })
        )
    