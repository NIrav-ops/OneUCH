from asgiref.sync import (
    async_to_sync,
)

from channels.routing import (
    URLRouter,
)

from channels.testing import (
    WebsocketCommunicator,
)

from django.contrib.auth import (
    get_user_model,
)

from django.test import (
    TestCase,
    override_settings,
)

from rest_framework_simplejwt.tokens import (
    RefreshToken,
)

from authentication.jwt_ws_middleware import (
    JWTAuthMiddleware,
    WS_AUTH_SUBPROTOCOL,
)

from inbox.routing import (
    websocket_urlpatterns,
)


User = get_user_model()


TEST_CHANNEL_LAYERS = {
    "default": {
        "BACKEND":
            "channels.layers.InMemoryChannelLayer",
    },
}


@override_settings(
    CHANNEL_LAYERS=TEST_CHANNEL_LAYERS
)
class WebSocketAuthenticationTransportTests(
    TestCase
):

    def setUp(self):

        self.user = (
            User.objects.create_user(
                email=(
                    "ws-auth@oneuch.local"
                ),
                password=(
                    "test-password-123"
                ),
            )
        )

        refresh = (
            RefreshToken.for_user(
                self.user
            )
        )

        self.access_token = str(
            refresh.access_token
        )

        self.application = (
            JWTAuthMiddleware(
                URLRouter(
                    websocket_urlpatterns
                )
            )
        )


    def test_subprotocol_jwt_authenticates_and_negotiates_marker(
        self,
    ):

        async def scenario():

            communicator = (
                WebsocketCommunicator(
                    self.application,
                    "/ws/inbox/",
                    subprotocols=[
                        WS_AUTH_SUBPROTOCOL,
                        self.access_token,
                    ],
                )
            )

            connected, selected = (
                await communicator.connect()
            )

            self.assertTrue(
                connected
            )

            self.assertEqual(
                selected,
                WS_AUTH_SUBPROTOCOL,
            )

            await communicator.disconnect()


        async_to_sync(
            scenario
        )()


    def test_query_string_jwt_is_rejected(
        self,
    ):

        async def scenario():

            communicator = (
                WebsocketCommunicator(
                    self.application,
                    (
                        "/ws/inbox/"
                        f"?token={self.access_token}"
                    ),
                )
            )

            connected, close_code = (
                await communicator.connect()
            )

            self.assertFalse(
                connected
            )

            self.assertEqual(
                close_code,
                4401,
            )


        async_to_sync(
            scenario
        )()


    def test_invalid_subprotocol_jwt_is_rejected(
        self,
    ):

        async def scenario():

            communicator = (
                WebsocketCommunicator(
                    self.application,
                    "/ws/inbox/",
                    subprotocols=[
                        WS_AUTH_SUBPROTOCOL,
                        "not-a-valid-jwt",
                    ],
                )
            )

            connected, close_code = (
                await communicator.connect()
            )

            self.assertFalse(
                connected
            )

            self.assertEqual(
                close_code,
                4401,
            )


        async_to_sync(
            scenario
        )()
