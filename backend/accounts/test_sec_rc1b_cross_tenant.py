from uuid import uuid4
from unittest.mock import patch

from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator

from django.test import (
    TestCase,
    override_settings,
)
from django.utils import timezone

from rest_framework.test import APIClient

from rest_framework_simplejwt.tokens import (
    RefreshToken,
)

from accounts.models import (
    User,
)

from actions.models import (
    ActionItem,
)

from approvals.models import (
    ApprovalItem,
)

from context.models import (
    BusinessObject,
    BusinessObjectType,
    Person,
)

from email_accounts.models import (
    EmailAccount,
)

from inbox.models import (
    Conversation,
    InboxMessage,
    Organization,
    OrganizationUser,
)

from notifications.models import (
    Notification,
)

from backend.asgi import application


TEST_CHANNEL_LAYERS = {
    "default": {
        "BACKEND": (
            "channels.layers."
            "InMemoryChannelLayer"
        ),
    },
}


@override_settings(
    CHANNEL_LAYERS=TEST_CHANNEL_LAYERS,
)
class SECRC1BCrossTenantAttackTests(
    TestCase
):
    """
    SEC-RC1B attack model:

    Tenant A and Tenant B are completely
    independent private workspaces.

    Every attack authenticates as Tenant A
    and attempts to access or mutate Tenant B.

    No real provider, broker, Redis, sync,
    send or AI execution is permitted.
    """

    PASSWORD = (
        "OneUCH!TenantTest93471"
    )

    def setUp(
        self,
    ):

        self.client = APIClient()

        (
            self.user_a,
            self.org_a,
        ) = self._tenant(
            "tenant-a@example.test"
        )

        (
            self.user_b,
            self.org_b,
        ) = self._tenant(
            "tenant-b@example.test"
        )

        self.account_a = (
            EmailAccount.objects.create(
                user=self.user_a,
                account_type="gmail",
                email_address=(
                    "mailbox-a@example.test"
                ),
                is_active=True,
            )
        )

        self.account_b = (
            EmailAccount.objects.create(
                user=self.user_b,
                account_type="gmail",
                email_address=(
                    "mailbox-b@example.test"
                ),
                is_active=True,
            )
        )

        self.conversation_a = (
            self._conversation(
                user=self.user_a,
                organization=self.org_a,
                account=self.account_a,
                label="a",
            )
        )

        self.conversation_b = (
            self._conversation(
                user=self.user_b,
                organization=self.org_b,
                account=self.account_b,
                label="b",
            )
        )

        self.message_a = (
            self._message(
                user=self.user_a,
                organization=self.org_a,
                account=self.account_a,
                conversation=(
                    self.conversation_a
                ),
                label="a",
            )
        )

        self.message_b = (
            self._message(
                user=self.user_b,
                organization=self.org_b,
                account=self.account_b,
                conversation=(
                    self.conversation_b
                ),
                label="b",
            )
        )

        self.action_a = (
            ActionItem.objects.create(
                user=self.user_a,
                organization=self.org_a,
                message=self.message_a,
                title="Tenant A Action",
                description="A only",
            )
        )

        self.action_b = (
            ActionItem.objects.create(
                user=self.user_b,
                organization=self.org_b,
                message=self.message_b,
                title=(
                    "Tenant B Secret Action"
                ),
                description="B only",
            )
        )

        self.approval_a = (
            ApprovalItem.objects.create(
                user=self.user_a,
                organization=self.org_a,
                message=self.message_a,
                conversation=(
                    self.conversation_a
                ),
                title="Tenant A Approval",
                description="A only",
            )
        )

        self.approval_b = (
            ApprovalItem.objects.create(
                user=self.user_b,
                organization=self.org_b,
                message=self.message_b,
                conversation=(
                    self.conversation_b
                ),
                title=(
                    "Tenant B Secret Approval"
                ),
                description="B only",
            )
        )

        Notification.objects.create(
            user=self.user_b,
            organization=self.org_b,
            type="system",
            title=(
                "Tenant B Secret Notice"
            ),
            message=(
                "Tenant B notification body"
            ),
        )

        object_type = (
            BusinessObjectType.objects
            .create(
                name=(
                    "SEC RC1B Customer"
                ),
                code=(
                    "SEC_RC1B_CUSTOMER_"
                    + uuid4().hex[:8]
                ),
            )
        )

        self.business_object_b = (
            BusinessObject.objects.create(
                organization=self.org_b,
                object_type=object_type,
                name=(
                    "Tenant B Business Object"
                ),
            )
        )

        self.person_b = (
            Person.objects.create(
                organization=self.org_b,
                email=(
                    "person-b@example.test"
                ),
                full_name=(
                    "Tenant B Person"
                ),
            )
        )

        self._authenticate(
            self.user_a
        )

    # ========================================================
    # FIXTURE HELPERS
    # ========================================================

    def _tenant(
        self,
        email,
    ):

        user = (
            User.objects.create_user(
                email=email,
                password=self.PASSWORD,
            )
        )

        organization = (
            Organization.objects.create(
                name="Private Workspace",
                slug=(
                    "workspace-"
                    + uuid4().hex
                ),
            )
        )

        OrganizationUser.objects.create(
            user=user,
            organization=organization,
            role="owner",
        )

        return (
            user,
            organization,
        )

    def _conversation(
        self,
        *,
        user,
        organization,
        account,
        label,
    ):

        return (
            Conversation.objects.create(
                user=user,
                organization=organization,
                email_account=account,
                subject=(
                    f"Conversation {label}"
                ),
                conversation_key=(
                    "sec-rc1b-"
                    + label
                    + "-"
                    + uuid4().hex
                ),
                last_message_at=(
                    timezone.now()
                ),
            )
        )

    def _message(
        self,
        *,
        user,
        organization,
        account,
        conversation,
        label,
    ):

        return (
            InboxMessage.objects.create(
                user=user,
                organization=organization,
                email_account=account,
                platform="gmail",
                direction="inbound",
                conversation=conversation,
                external_message_id=(
                    "sec-rc1b-msg-"
                    + label
                    + "-"
                    + uuid4().hex
                ),
                sender=(
                    f"sender-{label}"
                    "@example.test"
                ),
                recipients=(
                    f"recipient-{label}"
                    "@example.test"
                ),
                subject=(
                    f"Tenant {label.upper()} "
                    "Secret Subject"
                ),
                body=(
                    f"Tenant {label.upper()} "
                    "secret body"
                ),
                received_at=(
                    timezone.now()
                ),
                status="sent",
            )
        )

    def _authenticate(
        self,
        user,
    ):

        token = (
            RefreshToken.for_user(
                user
            ).access_token
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=(
                "Bearer "
                + str(token)
            )
        )

    def assert_hidden(
        self,
        response,
        *,
        allowed=(404,),
    ):

        self.assertIn(
            response.status_code,
            allowed,
            (
                response.data
                if hasattr(
                    response,
                    "data"
                )
                else None
            ),
        )

    # ========================================================
    # MESSAGE IDOR
    # ========================================================

    def test_tenant_a_cannot_read_tenant_b_message(
        self,
    ):

        response = self.client.get(
            (
                "/api/inbox/messages/"
                f"{self.message_b.id}/"
            )
        )

        self.assert_hidden(
            response
        )

    def test_tenant_a_cannot_read_tenant_b_message_status(
        self,
    ):

        response = self.client.get(
            (
                "/api/inbox/messages/"
                f"{self.message_b.id}/status/"
            )
        )

        self.assert_hidden(
            response
        )

    def test_tenant_a_cannot_change_tenant_b_read_state(
        self,
    ):

        response = self.client.post(
            (
                "/api/inbox/message/"
                f"{self.message_b.id}/"
                "read-state/"
            ),
            {
                "is_read": True,
            },
            format="json",
        )

        self.assert_hidden(
            response
        )

        self.message_b.refresh_from_db()

        self.assertFalse(
            self.message_b.is_read
        )

    def test_tenant_a_cannot_provider_open_tenant_b_message(
        self,
    ):

        response = self.client.get(
            (
                "/api/inbox/message/"
                f"{self.message_b.id}/"
                "provider-open/"
            )
        )

        self.assert_hidden(
            response
        )

    # ========================================================
    # CONVERSATION IDOR
    # ========================================================

    def test_tenant_a_cannot_read_tenant_b_conversation(
        self,
    ):

        response = self.client.get(
            (
                "/api/inbox/conversations/"
                f"{self.conversation_b.id}/"
            )
        )

        # Current legacy contract returns an
        # empty object for inaccessible IDs.
        #
        # That is accepted only if absolutely
        # no foreign content is disclosed.

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data,
            {
                "messages": [],
                "attachments": [],
            },
        )

    def test_tenant_a_cannot_mutate_tenant_b_conversation(
        self,
    ):

        response = self.client.post(
            (
                "/api/inbox/conversation/"
                f"{self.conversation_b.id}/"
                "mark-read/"
            ),
            {
                "is_read": True,
            },
            format="json",
        )

        self.assert_hidden(
            response
        )

    # ========================================================
    # ACTION / APPROVAL DIRECT OBJECT ATTACKS
    # ========================================================

    def test_tenant_a_cannot_complete_tenant_b_action(
        self,
    ):

        response = self.client.post(
            (
                "/api/actions/"
                f"{self.action_b.id}/"
                "complete/"
            ),
            {},
            format="json",
        )

        self.assert_hidden(
            response
        )

        self.action_b.refresh_from_db()

        self.assertEqual(
            self.action_b.status,
            "open",
        )

    def test_tenant_a_cannot_approve_tenant_b_approval(
        self,
    ):

        response = self.client.post(
            (
                "/api/approvals/"
                f"{self.approval_b.id}/"
                "approve/"
            ),
            {
                "decision_notes": (
                    "cross-tenant attempt"
                ),
            },
            format="json",
        )

        self.assert_hidden(
            response
        )

        self.approval_b.refresh_from_db()

        self.assertEqual(
            self.approval_b.status,
            "pending",
        )

    # ========================================================
    # FOREIGN ASSIGNEE INJECTION
    # ========================================================

    def test_action_assignee_cannot_be_foreign_tenant_user(
        self,
    ):

        before_notifications = (
            Notification.objects
            .filter(
                user=self.user_b
            )
            .count()
        )

        response = self.client.post(
            (
                "/api/actions/"
                f"{self.action_a.id}/"
                "assign/"
            ),
            {
                "owner": (
                    self.user_b.id
                ),
            },
            format="json",
        )

        self.assertIn(
            response.status_code,
            (
                400,
                404,
            ),
        )

        self.action_a.refresh_from_db()

        self.assertNotEqual(
            self.action_a.owner_id,
            self.user_b.id,
        )

        after_notifications = (
            Notification.objects
            .filter(
                user=self.user_b
            )
            .count()
        )

        self.assertEqual(
            before_notifications,
            after_notifications,
        )

    @patch(
        (
            "approvals.views."
            "send_approval_assignment_"
            "notification.delay"
        )
    )
    def test_approval_assignee_cannot_be_foreign_tenant_user(
        self,
        mocked_delay,
    ):

        response = self.client.post(
            (
                "/api/approvals/"
                f"{self.approval_a.id}/"
                "assign/"
            ),
            {
                "assigned_to": (
                    self.user_b.id
                ),
            },
            format="json",
        )

        self.assertIn(
            response.status_code,
            (
                400,
                404,
            ),
        )

        self.approval_a.refresh_from_db()

        self.assertNotEqual(
            self.approval_a.assigned_to_id,
            self.user_b.id,
        )

        mocked_delay.assert_not_called()

    # ========================================================
    # LIST / SEARCH / NOTIFICATION ATTACKS
    # ========================================================

    def test_action_list_does_not_expose_tenant_b(
        self,
    ):

        response = self.client.get(
            "/api/actions/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotIn(
            "Tenant B Secret Action",
            str(
                response.data
            ),
        )

    def test_approval_list_does_not_expose_tenant_b(
        self,
    ):

        response = self.client.get(
            "/api/approvals/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotIn(
            "Tenant B Secret Approval",
            str(
                response.data
            ),
        )

    def test_search_does_not_expose_tenant_b(
        self,
    ):

        response = self.client.get(
            "/api/search/",
            {
                "q": (
                    "Tenant B Secret"
                ),
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        result_body = str(
            {
                "results": (
                    response.data[
                        "results"
                    ]
                ),
                "grouped": (
                    response.data[
                        "grouped"
                    ]
                ),
            }
        )

        self.assertNotIn(
            "Tenant B Secret",
            result_body,
        )

        self.assertNotIn(
            "tenant b secret body",
            result_body.lower(),
        )

    def test_notifications_do_not_expose_tenant_b(
        self,
    ):

        response = self.client.get(
            "/api/notifications/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotIn(
            "Tenant B Secret Notice",
            str(
                response.data
            ),
        )

    def test_email_account_list_does_not_expose_tenant_b_mailbox(
        self,
    ):

        response = self.client.get(
            (
                "/api/email/"
                "email-accounts/"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        body = str(
            response.data
        )

        self.assertNotIn(
            "mailbox-b@example.test",
            body,
        )

    def test_tenant_a_cannot_read_tenant_b_signature(
        self,
    ):

        response = self.client.get(
            (
                "/api/email/"
                "mailbox-signature/"
                f"{self.account_b.id}/"
            )
        )

        self.assert_hidden(
            response
        )

    # ========================================================
    # CONTEXT / KNOWLEDGE IDOR
    # ========================================================

    def test_customer360_rejects_tenant_b_business_object(
        self,
    ):

        response = self.client.get(
            (
                "/api/context/customer360/"
                f"{self.business_object_b.id}/"
            )
        )

        self.assert_hidden(
            response
        )

    def test_people360_rejects_tenant_b_person(
        self,
    ):

        response = self.client.get(
            (
                "/api/context/people360/"
                f"{self.person_b.id}/"
            )
        )

        self.assert_hidden(
            response
        )

    def test_organization360_rejects_tenant_b_workspace(
        self,
    ):

        response = self.client.get(
            (
                "/api/context/"
                "organization360/"
                f"{self.org_b.id}/"
            )
        )

        self.assert_hidden(
            response
        )

    def test_context_search_rejects_tenant_b_workspace(
        self,
    ):

        response = self.client.get(
            (
                "/api/context/search/"
                f"{self.org_b.id}/"
            ),
            {
                "q": "secret",
            },
        )

        self.assert_hidden(
            response
        )

    # ========================================================
    # POISONED USER/ORGANIZATION ROW ATTACKS
    #
    # A row carrying:
    #
    #     user = Tenant A
    #     organization = Tenant B
    #
    # must not become visible merely because the
    # endpoint filters only by request.user.
    # ========================================================

    def test_mismatched_message_user_org_is_not_visible(
        self,
    ):

        poisoned = (
            InboxMessage.objects.create(
                user=self.user_a,
                organization=self.org_b,
                platform="gmail",
                direction="inbound",
                external_message_id=(
                    "poisoned-"
                    + uuid4().hex
                ),
                sender=(
                    "poison@example.test"
                ),
                recipients=(
                    "tenant-a@example.test"
                ),
                subject=(
                    "POISONED TENANT B MESSAGE"
                ),
                body=(
                    "must never be visible"
                ),
                received_at=(
                    timezone.now()
                ),
                status="sent",
            )
        )

        response = self.client.get(
            (
                "/api/inbox/messages/"
                f"{poisoned.id}/"
            )
        )

        self.assert_hidden(
            response
        )

    def test_mismatched_action_user_org_is_not_visible(
        self,
    ):

        poisoned = (
            ActionItem.objects.create(
                user=self.user_a,
                organization=self.org_b,
                title=(
                    "POISONED TENANT B ACTION"
                ),
                description=(
                    "must never be visible"
                ),
            )
        )

        response = self.client.get(
            "/api/actions/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotIn(
            poisoned.title,
            str(
                response.data
            ),
        )

    def test_mismatched_approval_user_org_is_not_visible(
        self,
    ):

        poisoned = (
            ApprovalItem.objects.create(
                user=self.user_a,
                organization=self.org_b,
                title=(
                    "POISONED TENANT B APPROVAL"
                ),
                description=(
                    "must never be visible"
                ),
            )
        )

        response = self.client.get(
            "/api/approvals/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotIn(
            poisoned.title,
            str(
                response.data
            ),
        )

    # ========================================================
    # WEBSOCKET AUTHORIZATION BOUNDARY
    # ========================================================

    def test_websocket_rejects_orphan_valid_jwt(
        self,
    ):

        orphan = (
            User.objects.create_user(
                email=(
                    "orphan-ws@example.test"
                ),
                password=self.PASSWORD,
            )
        )

        token = str(
            RefreshToken.for_user(
                orphan
            ).access_token
        )

        async def attack():

            communicator = (
                WebsocketCommunicator(
                    application,
                    "/ws/inbox/",
                    subprotocols=[
                        "oneuch.jwt",
                        token,
                    ],
                )
            )

            connected, _ = (
                await communicator.connect()
            )

            if connected:
                await communicator.disconnect()

            return connected

        connected = async_to_sync(
            attack
        )()

        self.assertFalse(
            connected
        )

    def test_websocket_rejects_inactive_workspace_valid_jwt(
        self,
    ):

        (
            user,
            organization,
        ) = self._tenant(
            "inactive-ws@example.test"
        )

        organization.is_active = False

        organization.save(
            update_fields=[
                "is_active"
            ]
        )

        token = str(
            RefreshToken.for_user(
                user
            ).access_token
        )

        async def attack():

            communicator = (
                WebsocketCommunicator(
                    application,
                    "/ws/inbox/",
                    subprotocols=[
                        "oneuch.jwt",
                        token,
                    ],
                )
            )

            connected, _ = (
                await communicator.connect()
            )

            if connected:
                await communicator.disconnect()

            return connected

        connected = async_to_sync(
            attack
        )()

        self.assertFalse(
            connected
        )