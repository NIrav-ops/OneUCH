import asyncio

from asgiref.sync import (
    async_to_sync,
)

from channels.db import (
    database_sync_to_async,
)

from channels.layers import (
    get_channel_layer,
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
    TransactionTestCase,
    override_settings,
)

from django.utils import (
    timezone,
)

from rest_framework_simplejwt.tokens import (
    RefreshToken,
)

from accounts.browser_session import (
    create_browser_session_tokens,
)

from authentication.jwt_ws_middleware import (
    JWTAuthMiddleware,
    WS_AUTH_SUBPROTOCOL,
)

from inbox.routing import (
    websocket_urlpatterns,
)

from inbox.models import (
    Organization,
    OrganizationUser,
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

        self.organization = (
            Organization.objects.create(
                name="WebSocket Test Workspace",
                slug="ws-auth-test-workspace",
            )
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=self.organization,
            role="owner",
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


    def test_active_browser_session_jwt_authenticates(
        self,
    ):

        (
            access,
            _refresh,
            returned_user,
            session,
        ) = (
            create_browser_session_tokens(
                self.user
            )
        )

        self.assertEqual(
            returned_user.id,
            self.user.id,
        )

        self.assertIsNone(
            session.revoked_at
        )


        async def scenario():

            communicator = (
                WebsocketCommunicator(
                    self.application,
                    "/ws/inbox/",
                    subprotocols=[
                        WS_AUTH_SUBPROTOCOL,
                        access,
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


    def test_revoked_browser_session_jwt_is_rejected(
        self,
    ):

        (
            access,
            _refresh,
            _returned_user,
            session,
        ) = (
            create_browser_session_tokens(
                self.user
            )
        )

        session.revoked_at = (
            timezone.now()
        )

        session.revocation_reason = (
            "logout"
        )

        session.save(
            update_fields=[
                "revoked_at",
                "revocation_reason",
            ]
        )


        async def scenario():

            communicator = (
                WebsocketCommunicator(
                    self.application,
                    "/ws/inbox/",
                    subprotocols=[
                        WS_AUTH_SUBPROTOCOL,
                        access,
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


@override_settings(
    CHANNEL_LAYERS=TEST_CHANNEL_LAYERS
)
class ExistingBrowserSessionSocketRevocationTests(
    TransactionTestCase
):

    reset_sequences = True


    def setUp(self):

        self.user = (
            User.objects.create_user(
                email=(
                    "ws-existing-session@oneuch.local"
                ),
                password=(
                    "test-password-123"
                ),
            )
        )

        self.organization = (
            Organization.objects.create(
                name=(
                    "Existing Session WebSocket Workspace"
                ),
                slug=(
                    "existing-session-ws-workspace"
                ),
            )
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=self.organization,
            role="owner",
        )

        self.application = (
            JWTAuthMiddleware(
                URLRouter(
                    websocket_urlpatterns
                )
            )
        )


    def test_existing_active_browser_session_receives_event(
        self,
    ):

        (
            access,
            _refresh,
            _returned_user,
            _session,
        ) = (
            create_browser_session_tokens(
                self.user
            )
        )


        async def scenario():

            communicator = (
                WebsocketCommunicator(
                    self.application,
                    "/ws/inbox/",
                    subprotocols=[
                        WS_AUTH_SUBPROTOCOL,
                        access,
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


            acceptance_id = (
                "active-browser-session-event"
            )


            await get_channel_layer().group_send(
                f"inbox_{self.user.id}",
                {
                    "type":
                        "inbox_update",

                    "data": {
                        "event":
                            "s4c_active_probe",

                        "acceptance_id":
                            acceptance_id,
                    },
                },
            )


            output = await asyncio.wait_for(
                communicator.receive_output(),
                timeout=2,
            )


            self.assertEqual(
                output.get(
                    "type"
                ),
                "websocket.send",
            )

            self.assertIn(
                acceptance_id,
                output.get(
                    "text"
                )
                or "",
            )


            await communicator.disconnect()


        async_to_sync(
            scenario
        )()


    def test_existing_browser_session_socket_closes_before_post_revocation_event_delivery(
        self,
    ):

        (
            access,
            _refresh,
            _returned_user,
            session,
        ) = (
            create_browser_session_tokens(
                self.user
            )
        )


        @database_sync_to_async
        def revoke_session():

            from accounts.models import (
                BrowserSession,
            )


            BrowserSession.objects.filter(
                pk=session.pk
            ).update(
                revoked_at=(
                    timezone.now()
                ),
                revocation_reason=(
                    "logout"
                ),
            )


        async def scenario():

            communicator = (
                WebsocketCommunicator(
                    self.application,
                    "/ws/inbox/",
                    subprotocols=[
                        WS_AUTH_SUBPROTOCOL,
                        access,
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


            await revoke_session()


            await get_channel_layer().group_send(
                f"inbox_{self.user.id}",
                {
                    "type":
                        "inbox_update",

                    "data": {
                        "event":
                            "s4c_revocation_probe",

                        "acceptance_id":
                            "must-not-be-delivered",
                    },
                },
            )


            output = await asyncio.wait_for(
                communicator.receive_output(),
                timeout=2,
            )


            self.assertEqual(
                output.get(
                    "type"
                ),
                "websocket.close",
            )

            self.assertEqual(
                output.get(
                    "code"
                ),
                4401,
            )


        async_to_sync(
            scenario
        )()
