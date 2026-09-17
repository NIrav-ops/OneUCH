
from datetime import timedelta

from django.contrib.auth import (
    get_user_model,
)

from django.utils import timezone

from rest_framework.test import (
    APITestCase,
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


User = get_user_model()


class ConversationChronologyTests(
    APITestCase
):

    def setUp(
        self,
    ):

        self.user = (
            User.objects.create_user(
                email=(
                    "chronology@oneuch.test"
                ),
                password="pass123",
            )
        )


        self.organization = (
            Organization.objects.create(
                name=(
                    "Chronology Organization"
                ),
                slug=(
                    "chronology-organization"
                ),
            )
        )


        OrganizationUser.objects.create(
            user=self.user,
            organization=(
                self.organization
            ),
            role="member",
        )


        self.account = (
            EmailAccount.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                email_address=(
                    "chronology@example.test"
                ),
                account_type="imap",
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
                subject="Chronology test",
                conversation_key=(
                    "chronology-test"
                ),
                external_conversation_id=(
                    "provider-thread-1"
                ),
            )
        )


        base = timezone.now()


        self.first_inbox = (
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
                    "chronology-1"
                ),
                external_conversation_id=(
                    "provider-thread-1"
                ),
                sender=(
                    "customer@example.test"
                ),
                recipients=(
                    self.account.email_address
                ),
                subject=(
                    "Chronology test"
                ),
                body=(
                    "Initial customer message"
                ),
                received_at=base,
                is_draft=False,
                status="queued",
            )
        )


        self.latest_inbox = (
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
                    "chronology-2"
                ),
                external_conversation_id=(
                    "provider-thread-1"
                ),
                sender=(
                    "customer@example.test"
                ),
                recipients=(
                    self.account.email_address
                ),
                subject=(
                    "RE: Chronology test"
                ),
                body=(
                    "Latest Inbox content"
                ),
                received_at=(
                    base
                    + timedelta(
                        hours=1
                    )
                ),
                is_draft=False,
                status="queued",
            )
        )


        self.latest_sent = (
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
                folder="sent",
                direction="outbound",
                external_message_id=(
                    "chronology-3"
                ),
                external_conversation_id=(
                    "provider-thread-1"
                ),
                sender=(
                    self.account.email_address
                ),
                recipients=(
                    "customer@example.test"
                ),
                subject=(
                    "RE: Chronology test"
                ),
                body=(
                    "Latest Sent content"
                ),
                received_at=(
                    base
                    + timedelta(
                        hours=2
                    )
                ),
                is_draft=False,
                status="sent",
            )
        )


        self.conversation.last_message = (
            self.latest_sent
        )

        self.conversation.last_message_at = (
            self.latest_sent.received_at
        )

        self.conversation.last_message_preview = (
            self.latest_sent.body
        )

        self.conversation.save(
            update_fields=[
                "last_message",
                "last_message_at",
                "last_message_preview",
            ]
        )


        self.client.force_authenticate(
            user=self.user
        )


    def test_conversation_detail_is_chronological(
        self,
    ):

        response = self.client.get(
            (
                "/api/inbox/conversations/"
                + str(
                    self.conversation.id
                )
                + "/"
            ),
            secure=True,
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        messages = (
            response.data[
                "messages"
            ]
        )


        self.assertEqual(
            [
                item["id"]
                for item in messages
            ],
            [
                self.first_inbox.id,
                self.latest_inbox.id,
                self.latest_sent.id,
            ],
        )


        self.assertEqual(
            [
                item["folder"]
                for item in messages
            ],
            [
                "inbox",
                "inbox",
                "sent",
            ],
        )


    def test_inbox_rail_uses_latest_inbox_message(
        self,
    ):

        response = self.client.get(
            (
                "/api/inbox/"
                "unified-conversations/"
                "?folder=inbox"
                "&account_id="
                + str(
                    self.account.id
                )
            ),
            secure=True,
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        result = (
            response.data[
                "results"
            ][0]
        )


        self.assertEqual(
            result["subject"],
            self.latest_inbox.subject,
        )

        self.assertEqual(
            result["preview"],
            (
                self.latest_inbox
                .body[:120]
            ),
        )

        self.assertEqual(
            result["sender"],
            self.latest_inbox.sender,
        )


    def test_sent_rail_uses_latest_sent_message(
        self,
    ):

        response = self.client.get(
            (
                "/api/inbox/"
                "unified-conversations/"
                "?folder=sent"
                "&account_id="
                + str(
                    self.account.id
                )
            ),
            secure=True,
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        result = (
            response.data[
                "results"
            ][0]
        )


        self.assertEqual(
            result["subject"],
            self.latest_sent.subject,
        )

        self.assertEqual(
            result["preview"],
            (
                self.latest_sent
                .body[:120]
            ),
        )

        self.assertEqual(
            result["recipients"],
            self.latest_sent.recipients,
        )
