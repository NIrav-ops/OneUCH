import json

from channels.generic.websocket import AsyncWebsocketConsumer

from authentication.jwt_ws_middleware import (
    WS_AUTH_SUBPROTOCOL,
)


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


    async def inbox_update(self, event):

        await self.send(
            text_data=json.dumps(event["data"])
        )

    async def send_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "update"
        }))
    