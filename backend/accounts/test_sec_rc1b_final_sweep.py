from uuid import uuid4
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from rest_framework.test import APIClient

from rest_framework_simplejwt.tokens import (
    RefreshToken,
)

from accounts.models import User

from email_accounts.models import (
    EmailAccount,
)

from inbox.models import (
    Conversation,
    InboxMessage,
    Organization,
    OrganizationUser,
)


class SECRC1BFinalIsolationSweepTests(
    TestCase
):
    """
    Final SEC-RC1B attack sweep.

    The attacker owns User A but attempts to
    operate on deliberately inconsistent rows:

        user = Tenant A
        organization = Tenant B

    Provider mutation functions and queued
    Reply delivery are mocked so this suite
    cannot touch real mail/provider systems.
    """

    PASSWORD = (
        "OneUCH!FinalSweep93471"
    )

    POISON = (
        "SEC-RC1B-B5-POISON-7D91"
    )

    def setUp(
        self,
    ):

        self.client = APIClient()

        (
            self.user_a,
            self.org_a,
        ) = self._tenant(
            "tenant-a-b5@example.test"
        )

        (
            self.user_b,
            self.org_b,
        ) = self._tenant(
            "tenant-b-b5@example.test"
        )

        self.account_a = (
            EmailAccount.objects.create(
                user=self.user_a,
                account_type="gmail",
                email_address=(
                    "mailbox-a-b5@example.test"
                ),
                is_active=True,
            )
        )

        # ----------------------------------------------------
        # Legitimate Tenant A data
        # ----------------------------------------------------

        self.conv_a = (
            self._conversation(
                organization=self.org_a,
                label="clean",
            )
        )

        self.msg_a = (
            self._message(
                organization=self.org_a,
                conversation=self.conv_a,
                label="clean",
                subject=(
                    "Tenant A clean message"
                ),
            )
        )

        # ----------------------------------------------------
        # Poisoned ownership data
        #
        # user = A
        # organization = B
        #
        # Same User and mailbox intentionally make
        # user-only query filters insufficient.
        # ----------------------------------------------------

        self.poison_conv = (
            self._conversation(
                organization=self.org_b,
                label="poison",
            )
        )

        self.poison_msg = (
            self._message(
                organization=self.org_b,
                conversation=(
                    self.poison_conv
                ),
                label="poison",
                subject=(
                    self.POISON
                    + " MESSAGE"
                ),
                attachment_meta=[
                    {
                        "attachment_id":
                            "poison-attachment",
                        "filename":
                            "poison.txt",
                        "mime_type":
                            "text/plain",
                    }
                ],
            )
        )

        self._authenticate(
            self.user_a
        )

    # ========================================================
    # FIXTURES
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
                    "sec-rc1b-b5-"
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
        organization,
        label,
    ):

        return (
            Conversation.objects.create(
                user=self.user_a,
                organization=organization,
                email_account=self.account_a,
                subject=(
                    "B5 "
                    + label
                    + " conversation"
                ),
                conversation_key=(
                    "b5-"
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
        organization,
        conversation,
        label,
        subject,
        attachment_meta=None,
    ):

        return (
            InboxMessage.objects.create(
                user=self.user_a,
                organization=organization,
                email_account=self.account_a,
                platform="gmail",
                direction="inbound",
                conversation=conversation,
                external_message_id=(
                    "b5-provider-"
                    + label
                    + "-"
                    + uuid4().hex
                ),
                sender=(
                    label
                    + "@sender.test"
                ),
                recipients=(
                    self.user_a.email
                ),
                subject=subject,
                body=(
                    subject
                    + " BODY"
                ),
                attachment_meta=(
                    attachment_meta
                    or []
                ),
                received_at=(
                    timezone.now()
                ),
                folder="inbox",
                status="sent",
                is_read=False,
                is_starred=False,
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

    # ========================================================
    # LEGACY CONVERSATION READ SURFACES
    # ========================================================

    def test_conversation_list_excludes_poisoned_workspace(
        self,
    ):

        response = self.client.get(
            "/api/inbox/conversations/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        ids = [
            item.get(
                "conversation_id"
            )
            for item
            in response.data
        ]

        self.assertNotIn(
            self.poison_conv.id,
            ids,
        )

    def test_conversation_detail_excludes_poisoned_workspace(
        self,
    ):

        response = self.client.get(
            (
                "/api/inbox/conversations/"
                f"{self.poison_conv.id}/"
            )
        )

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

        self.assertNotIn(
            self.POISON,
            str(response.data),
        )

    # ========================================================
    # SINGLE CONVERSATION MUTATIONS
    # ========================================================

    def test_poisoned_conversation_mark_read_is_blocked(
        self,
    ):

        with patch(
            (
                "inbox.views."
                "conversation_actions."
                "set_conversation_read"
            )
        ) as mocked:

            mocked.return_value = {
                "updated": 1,
                "errors": [],
            }

            response = self.client.post(
                (
                    "/api/inbox/conversation/"
                    f"{self.poison_conv.id}/"
                    "mark-read/"
                ),
                {
                    "is_read": True,
                },
                format="json",
            )

        self.assertEqual(
            response.status_code,
            404,
        )

        mocked.assert_not_called()

        self.poison_msg.refresh_from_db()

        self.assertFalse(
            self.poison_msg.is_read
        )

    def test_poisoned_conversation_star_is_blocked(
        self,
    ):

        with patch(
            (
                "inbox.views."
                "conversation_actions."
                "set_conversation_star"
            )
        ) as mocked:

            mocked.return_value = {
                "updated": 1,
                "errors": [],
            }

            response = self.client.post(
                (
                    "/api/inbox/conversation/"
                    f"{self.poison_conv.id}/"
                    "toggle-star/"
                ),
                {},
                format="json",
            )

        self.assertEqual(
            response.status_code,
            404,
        )

        mocked.assert_not_called()

    def test_poisoned_conversation_delete_is_blocked(
        self,
    ):

        with patch(
            (
                "inbox.views."
                "conversation_actions."
                "trash_conversation"
            )
        ) as mocked:

            mocked.return_value = {
                "updated": 1,
                "errors": [],
            }

            response = self.client.post(
                (
                    "/api/inbox/conversation/"
                    f"{self.poison_conv.id}/"
                    "delete/"
                ),
                {},
                format="json",
            )

        self.assertEqual(
            response.status_code,
            404,
        )

        mocked.assert_not_called()

    # ========================================================
    # BULK CONVERSATION MUTATIONS
    # ========================================================

    def test_bulk_mark_read_ignores_poisoned_workspace(
        self,
    ):

        with patch(
            (
                "inbox.views."
                "conversation_bulk."
                "set_conversation_read"
            )
        ) as mocked:

            mocked.return_value = {
                "updated": 1,
                "errors": [],
            }

            response = self.client.post(
                (
                    "/api/inbox/conversation/"
                    "bulk-mark-read/"
                ),
                {
                    "conversation_ids": [
                        self.poison_conv.id
                    ],
                    "is_read": True,
                },
                format="json",
            )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data[
                "updated"
            ],
            [],
        )

        self.assertEqual(
            response.data[
                "errors"
            ],
            [],
        )

        mocked.assert_not_called()

    def test_bulk_toggle_star_ignores_poisoned_workspace(
        self,
    ):

        with patch(
            (
                "inbox.views."
                "conversation_bulk."
                "set_conversation_star"
            )
        ) as mocked:

            mocked.return_value = {
                "updated": 1,
                "errors": [],
            }

            response = self.client.post(
                (
                    "/api/inbox/conversation/"
                    "bulk-toggle-star/"
                ),
                {
                    "conversation_ids": [
                        self.poison_conv.id
                    ],
                    "is_starred": True,
                },
                format="json",
            )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data[
                "updated"
            ],
            [],
        )

        self.assertEqual(
            response.data[
                "errors"
            ],
            [],
        )

        mocked.assert_not_called()

    # ========================================================
    # SINGLE MESSAGE MUTATIONS
    # ========================================================

    def test_poisoned_message_read_state_is_blocked(
        self,
    ):

        with patch(
            (
                "inbox.views."
                "message_read."
                "set_message_read"
            )
        ) as mocked:

            response = self.client.post(
                (
                    "/api/inbox/message/"
                    f"{self.poison_msg.id}/"
                    "read-state/"
                ),
                {
                    "is_read": True,
                },
                format="json",
            )

        self.assertEqual(
            response.status_code,
            404,
        )

        mocked.assert_not_called()

        self.poison_msg.refresh_from_db()

        self.assertFalse(
            self.poison_msg.is_read
        )

    def test_poisoned_message_star_is_blocked(
        self,
    ):

        with patch(
            (
                "inbox.views."
                "star."
                "set_message_star"
            )
        ) as mocked:

            response = self.client.post(
                (
                    "/api/inbox/message/"
                    f"{self.poison_msg.id}/"
                    "toggle-star/"
                ),
                {},
                format="json",
            )

        self.assertEqual(
            response.status_code,
            404,
        )

        mocked.assert_not_called()

    def test_poisoned_message_delete_is_blocked(
        self,
    ):

        with patch(
            (
                "inbox.views."
                "delete."
                "trash_message"
            )
        ) as mocked:

            response = self.client.post(
                (
                    "/api/inbox/message/"
                    f"{self.poison_msg.id}/"
                    "delete/"
                ),
                {},
                format="json",
            )

        self.assertEqual(
            response.status_code,
            404,
        )

        mocked.assert_not_called()

    # ========================================================
    # PROVIDER OPEN
    # ========================================================

    def test_provider_open_rejects_poisoned_workspace(
        self,
    ):

        with patch(
            (
                "inbox.views."
                "provider_open."
                "provider_open_url"
            )
        ) as mocked:

            mocked.return_value = (
                "https://example.test/open"
            )

            response = self.client.get(
                (
                    "/api/inbox/message/"
                    f"{self.poison_msg.id}/"
                    "provider-open/"
                )
            )

        self.assertEqual(
            response.status_code,
            404,
        )

        mocked.assert_not_called()

    # ========================================================
    # BULK MESSAGE STATUS
    # B4 should already protect this.
    # ========================================================

    def test_bulk_status_excludes_poisoned_workspace(
        self,
    ):

        response = self.client.post(
            (
                "/api/inbox/messages/"
                "status/bulk/"
            ),
            {
                "message_ids": [
                    self.msg_a.id,
                    self.poison_msg.id,
                ]
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        returned_ids = [
            item.get(
                "id"
            )
            for item
            in response.data
        ]

        self.assertIn(
            self.msg_a.id,
            returned_ids,
        )

        self.assertNotIn(
            self.poison_msg.id,
            returned_ids,
        )

    # ========================================================
    # PROVIDER ATTACHMENT SECONDARY ID
    #
    # Existing implementation has an explicit
    # organization check. Provider clients must
    # never be reached.
    # ========================================================

    def test_attachment_secondary_id_is_tenant_scoped(
        self,
    ):

        with patch(
            (
                "inbox.views_attachment."
                "get_gmail_credentials"
            )
        ) as mocked_creds:

            with patch(
                (
                    "inbox.views_attachment."
                    "build"
                )
            ) as mocked_build:

                response = self.client.get(
                    (
                        "/api/inbox/attachments/"
                        f"{self.poison_msg.id}/"
                        "poison-attachment/"
                    )
                )

        self.assertEqual(
            response.status_code,
            404,
        )

        mocked_creds.assert_not_called()
        mocked_build.assert_not_called()

    # ========================================================
    # LEGACY INBOX SEARCH
    # ========================================================

    def test_legacy_inbox_search_excludes_poisoned_workspace(
        self,
    ):

        response = self.client.get(
            "/api/inbox/search/",
            {
                "q": self.POISON,
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotIn(
            self.POISON,
            str(response.data),
        )

    # ========================================================
    # FORWARD PREFLIGHT
    #
    # GET is strictly read-only; no source attachment
    # content is downloaded during preflight.
    # ========================================================

    def test_forward_preflight_rejects_poisoned_workspace(
        self,
    ):

        response = self.client.get(
            (
                "/api/inbox/message/"
                f"{self.poison_msg.id}/"
                "forward/"
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertNotIn(
            str(
                self.poison_msg.id
            ),
            str(response.data),
        )

    # ========================================================
    # REPLY
    #
    # Provider delivery task is mocked.
    # A foreign-workspace conversation must be
    # rejected before local outbound creation or queueing.
    # ========================================================

    def test_reply_rejects_poisoned_workspace(
        self,
    ):

        before_messages = (
            InboxMessage.objects.count()
        )

        with patch(
            (
                "inbox.views.reply."
                "prepare_outbound_attachments"
            ),
            return_value=[],
        ):

            with patch(
                (
                    "inbox.views.reply."
                    "send_email_task.delay"
                )
            ) as mocked_send:

                response = self.client.post(
                    (
                        "/api/inbox/conversations/"
                        f"{self.poison_conv.id}/"
                        "reply/"
                    ),
                    {
                        "body": (
                            "Cross-workspace reply attempt"
                        ),
                        "mode": "reply",
                    },
                    format="json",
                )

        self.assertEqual(
            response.status_code,
            404,
        )

        mocked_send.assert_not_called()

        self.assertEqual(
            InboxMessage.objects.count(),
            before_messages,
        )

    # ========================================================
    # NESTED POISONED CHILD
    # ========================================================

    def test_valid_conversation_excludes_poisoned_child_message(
        self,
    ):

        poisoned_child = (
            InboxMessage.objects.create(
                user=self.user_a,
                organization=self.org_b,
                email_account=self.account_a,
                platform="gmail",
                direction="inbound",
                conversation=self.conv_a,
                external_message_id=(
                    "b6-child-"
                    + uuid4().hex
                ),
                sender=(
                    "nested-poison@sender.test"
                ),
                recipients=self.user_a.email,
                subject=(
                    self.POISON
                    + " NESTED CHILD"
                ),
                body=(
                    self.POISON
                    + " NESTED CHILD BODY"
                ),
                received_at=timezone.now(),
                folder="inbox",
                status="sent",
            )
        )

        response = self.client.get(
            (
                "/api/inbox/conversations/"
                f"{self.conv_a.id}/"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotIn(
            poisoned_child.id,
            [
                item.get("id")
                for item
                in response.data.get(
                    "messages",
                    [],
                )
            ],
        )

        self.assertNotIn(
            self.POISON,
            str(response.data),
        )


    # ========================================================
    # COMPOSE/SEND EXPLICIT CONVERSATION
    # ========================================================

    def test_send_rejects_poisoned_conversation(
        self,
    ):

        before_messages = (
            InboxMessage.objects.count()
        )

        with patch(
            (
                "inbox.views.send_message."
                "prepare_outbound_attachments"
            ),
            return_value=[],
        ):

            with patch(
                (
                    "inbox.views.send_message."
                    "get_gmail_credentials"
                )
            ) as mocked_creds:

                with patch(
                    (
                        "inbox.views.send_message."
                        "build"
                    )
                ) as mocked_build:

                    response = self.client.post(
                        "/api/inbox/send/",
                        {
                            "account_id":
                                self.account_a.id,

                            "conversation_id":
                                self.poison_conv.id,

                            "to": [
                                "recipient@example.test"
                            ],

                            "subject":
                                "B6 tenant boundary",

                            "body":
                                "must not send",
                        },
                        format="json",
                    )

        self.assertEqual(
            response.status_code,
            404,
        )

        mocked_creds.assert_not_called()
        mocked_build.assert_not_called()

        self.assertEqual(
            InboxMessage.objects.count(),
            before_messages,
        )
