from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from django.test import TestCase
from django.utils import timezone

from rest_framework.test import APITestCase

from accounts.models import User
from email_accounts.models import EmailAccount

from inbox.models import (
    Conversation,
    InboxMessage,
    Organization,
    OrganizationUser,
)

from inbox.tasks import (
    _broadcast_inbox_sync_event,
    _pending_mail_intelligence_message_ids,
    sync_email_account,
)


class MailSyncRealtimeTests(
    TestCase
):

    def test_success_event_targets_user_inbox_group(
        self,
    ):
        account = SimpleNamespace(
            id=41,
            user_id=73,
            account_type="imap",
        )

        layer = SimpleNamespace(
            group_send=Mock()
        )

        sender = Mock()

        with (
            patch(
                "inbox.tasks.get_channel_layer",
                return_value=layer,
            ),
            patch(
                "inbox.tasks.async_to_sync",
                return_value=sender,
            ),
        ):
            result = (
                _broadcast_inbox_sync_event(
                    account=account,
                    event="sync_completed",
                )
            )

        self.assertTrue(
            result
        )

        sender.assert_called_once_with(
            "inbox_73",
            {
                "type":
                    "inbox_update",

                "data": {
                    "event":
                        "sync_completed",

                    "account_id":
                        41,

                    "provider":
                        "imap",
                },
            },
        )


    def test_imap_sync_reconciles_trash_and_broadcasts_completion(
        self,
    ):
        user = (
            User.objects.create_user(
                email=(
                    "sync-realtime@oneuch.test"
                ),
                password="pass123",
            )
        )

        organization = (
            Organization.objects.create(
                name="Realtime Workspace",
                slug=(
                    "realtime-"
                    + uuid4().hex
                ),
            )
        )

        OrganizationUser.objects.create(
            user=user,
            organization=organization,
            role="owner",
        )

        account = (
            EmailAccount.objects.create(
                user=user,
                organization=organization,
                account_type="imap",
                email_address=(
                    "sync@example.com"
                ),
                imap_server=(
                    "imap.example.com"
                ),
                imap_port=993,
                smtp_server=(
                    "smtp.example.com"
                ),
                smtp_port=465,
                smtp_password=(
                    "Synthetic-Sync-Credential-92814"
                ),
                credential_status="active",
                is_active=True,
            )
        )

        with (
            patch(
                "inbox.tasks.acquire_sync_lock",
                return_value="test-lock",
            ) as acquire_mock,
            patch(
                "inbox.tasks.release_sync_lock"
            ) as release_mock,
            patch(
                "inbox.tasks.fetch_imap_emails"
            ) as fetch_mock,
            patch(
                "inbox.tasks.reconcile_imap_trash"
            ) as reconcile_mock,
            patch(
                (
                    "inbox.tasks."
                    "_queue_scoped_mail_intelligence"
                ),
                return_value={
                    "message_count": 0,
                    "batch_count": 0,
                },
            ),
            patch(
                (
                    "inbox.tasks."
                    "_broadcast_inbox_sync_event"
                )
            ) as broadcast_mock,
        ):
            result = (
                sync_email_account.run(
                    account.id
                )
            )

            acquire_mock.assert_called_once_with(
                account.id,
                timeout=7200,
            )

        self.assertEqual(
            result[
                "status"
            ],
            "completed",
        )

        fetch_mock.assert_called_once()

        reconcile_mock.assert_called_once()

        reconcile_kwargs = (
            reconcile_mock
            .call_args
            .kwargs
        )

        self.assertEqual(
            reconcile_kwargs[
                "user"
            ].id,
            user.id,
        )

        self.assertEqual(
            reconcile_kwargs[
                "email_account"
            ].id,
            account.id,
        )

        broadcast_mock.assert_called_once()

        broadcast_kwargs = (
            broadcast_mock
            .call_args
            .kwargs
        )

        self.assertEqual(
            broadcast_kwargs[
                "account"
            ].id,
            account.id,
        )

        self.assertEqual(
            broadcast_kwargs[
                "event"
            ],
            "sync_completed",
        )

        release_mock.assert_called_once_with(
            "test-lock"
        )



    def test_trash_messages_are_excluded_from_intelligence_handoff(
        self,
    ):
        user = (
            User.objects.create_user(
                email=(
                    "trash-intelligence@oneuch.test"
                ),
                password="pass123",
            )
        )

        organization = (
            Organization.objects.create(
                name="Trash Intelligence Workspace",
                slug=(
                    "trash-intel-"
                    + uuid4().hex
                ),
            )
        )

        OrganizationUser.objects.create(
            user=user,
            organization=organization,
            role="owner",
        )

        account = (
            EmailAccount.objects.create(
                user=user,
                organization=organization,
                account_type="imap",
                email_address=(
                    "trash-intelligence@example.com"
                ),
                credential_status="active",
                is_active=True,
            )
        )

        conversation = (
            Conversation.objects.create(
                user=user,
                organization=organization,
                email_account=account,
                subject="Intelligence",
                conversation_key=(
                    "trash-intelligence-"
                    + uuid4().hex
                ),
            )
        )

        active_message = (
            InboxMessage.objects.create(
                user=user,
                organization=organization,
                email_account=account,
                conversation=conversation,
                platform="imap",
                folder="inbox",
                direction="inbound",
                external_message_id=(
                    "imap-rfc822-active-test"
                ),
                sender="sender@example.net",
                recipients=(
                    account.email_address
                ),
                subject="Active",
                body="Active body",
                received_at=timezone.now(),
                status="queued",
            )
        )

        trash_message = (
            InboxMessage.objects.create(
                user=user,
                organization=organization,
                email_account=account,
                conversation=conversation,
                platform="imap",
                folder="trash",
                direction="inbound",
                external_message_id=(
                    "imap-rfc822-trash-test"
                ),
                sender="sender@example.net",
                recipients=(
                    account.email_address
                ),
                subject="Trash",
                body="Trash body",
                received_at=timezone.now(),
                status="queued",
            )
        )

        message_ids = (
            _pending_mail_intelligence_message_ids(
                account=account
            )
        )

        self.assertIn(
            active_message.id,
            message_ids,
        )

        self.assertNotIn(
            trash_message.id,
            message_ids,
        )



class IMAPConversationDeleteAPITests(
    APITestCase
):

    def setUp(self):
        self.user = (
            User.objects.create_user(
                email=(
                    "imap-delete@oneuch.test"
                ),
                password="pass123",
            )
        )

        self.organization = (
            Organization.objects.create(
                name="Delete Workspace",
                slug=(
                    "delete-"
                    + uuid4().hex
                ),
            )
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=(
                self.organization
            ),
            role="owner",
        )

        self.account = (
            EmailAccount.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                account_type="imap",
                email_address=(
                    "delete@example.com"
                ),
                imap_server=(
                    "imap.example.com"
                ),
                imap_port=993,
                smtp_server=(
                    "smtp.example.com"
                ),
                smtp_port=465,
                smtp_password=(
                    "Synthetic-Delete-Credential-58312"
                ),
                credential_status="active",
                is_active=True,
            )
        )

        self.conversation = (
            Conversation.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                email_account=(
                    self.account
                ),
                subject="Delete",
                conversation_key=(
                    "delete-"
                    + uuid4().hex
                ),
            )
        )

        InboxMessage.objects.create(
            user=self.user,
            organization=(
                self.organization
            ),
            email_account=(
                self.account
            ),
            conversation=(
                self.conversation
            ),
            platform="imap",
            folder="inbox",
            direction="inbound",
            external_message_id=(
                "imap-rfc822-test"
            ),
            sender=(
                "sender@example.net"
            ),
            recipients=(
                self.account.email_address
            ),
            subject="Delete",
            body="Body",
            received_at=(
                timezone.now()
            ),
            status="queued",
        )


    @patch(
        (
            "inbox.views."
            "conversation_actions."
            "trash_imap_conversation"
        )
    )
    def test_delete_uses_governed_imap_service_without_browser_password(
        self,
        trash_mock,
    ):
        trash_mock.return_value = {
            "status":
                "completed",

            "updated":
                1,

            "moved":
                1,
        }

        self.client.force_authenticate(
            user=self.user
        )

        response = (
            self.client.post(
                (
                    "/api/inbox/conversation/"
                    + str(
                        self.conversation.id
                    )
                    + "/delete/"
                ),
                {},
                format="json",
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data[
                "status"
            ],
            "conversation_deleted",
        )

        trash_mock.assert_called_once()

        kwargs = (
            trash_mock
            .call_args
            .kwargs
        )

        self.assertEqual(
            kwargs[
                "conversation"
            ].id,
            self.conversation.id,
        )

        self.assertEqual(
            kwargs[
                "user"
            ].id,
            self.user.id,
        )
