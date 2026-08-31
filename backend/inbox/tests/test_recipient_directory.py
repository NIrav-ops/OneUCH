from datetime import (
    timedelta,
)

from django.contrib.auth import (
    get_user_model,
)

from django.test import (
    TestCase,
)

from django.utils import (
    timezone,
)

from rest_framework.test import (
    APIClient,
)

from email_accounts.models import (
    EmailAccount,
)

from inbox.models import (
    InboxMessage,
    Organization,
    OrganizationUser,
    RecipientContact,
    RecipientDirectoryState,
)

from inbox.services.recipient_directory import (
    refresh_recipient_directory,
    suggest_recipients,
)


User = get_user_model()


class RecipientDirectoryTests(
    TestCase
):

    def setUp(
        self,
    ):
        self.user = (
            User.objects.create_user(
                email=(
                    "recipient-owner@oneuch.test"
                ),
                password="pass123",
            )
        )

        self.organization = (
            Organization.objects.create(
                name=(
                    "Recipient Directory Org"
                ),
                slug=(
                    "recipient-directory-org"
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
                account_type="gmail",
                email_address=(
                    "owner@gmail.com"
                ),
                is_active=True,
            )
        )

        self.client = (
            APIClient()
        )


    def message(
        self,
        *,
        external_id,
        direction,
        sender,
        recipients,
        sender_meta=None,
        recipient_meta=None,
        received_at=None,
        user=None,
        organization=None,
        account=None,
    ):
        user = (
            user
            or
            self.user
        )

        organization = (
            organization
            or
            self.organization
        )

        account = (
            account
            or
            self.account
        )

        return (
            InboxMessage.objects.create(
                user=user,
                organization=(
                    organization
                ),
                email_account=(
                    account
                ),
                platform=(
                    account.account_type
                ),
                direction=direction,
                folder=(
                    "sent"
                    if direction
                    ==
                    "outbound"
                    else "inbox"
                ),
                external_message_id=(
                    external_id
                ),
                sender=sender,
                recipients=(
                    recipients
                ),
                sender_meta=(
                    sender_meta
                    or {}
                ),
                recipient_meta=(
                    recipient_meta
                    or {}
                ),
                subject=(
                    "Recipient directory"
                ),
                body="Body",
                received_at=(
                    received_at
                    or
                    timezone.now()
                ),
                is_read=True,
                status=(
                    "sent"
                    if direction
                    ==
                    "outbound"
                    else "queued"
                ),
            )
        )


    def test_builds_contact_counts_from_sender_to_cc_bcc(
        self,
    ):
        older = (
            timezone.now()
            -
            timedelta(
                days=2
            )
        )

        newer = (
            timezone.now()
            -
            timedelta(
                hours=1
            )
        )


        self.message(
            external_id="incoming-1",
            direction="inbound",
            sender=(
                "alice@example.com"
            ),
            recipients=(
                self.account
                .email_address
            ),
            sender_meta={
                "name":
                    "Alice Example",
                "email":
                    "alice@example.com",
            },
            recipient_meta={
                "to": [
                    {
                        "name":
                            "",
                        "email":
                            self.account
                            .email_address,
                    }
                ],
                "cc": [],
                "bcc": [],
                "reply_to": [
                    {
                        "name":
                            "Alice Example",
                        "email":
                            "alice@example.com",
                    }
                ],
            },
            received_at=older,
        )


        self.message(
            external_id="outgoing-1",
            direction="outbound",
            sender=(
                self.account
                .email_address
            ),
            recipients=(
                "alice@example.com, "
                "bob@example.com, "
                "carol@example.com"
            ),
            sender_meta={
                "name":
                    "",
                "email":
                    self.account
                    .email_address,
            },
            recipient_meta={
                "to": [
                    {
                        "name":
                            "Alice Example",
                        "email":
                            "alice@example.com",
                    }
                ],
                "cc": [
                    {
                        "name":
                            "Bob Finance",
                        "email":
                            "bob@example.com",
                    }
                ],
                "bcc": [
                    {
                        "name":
                            "Carol Audit",
                        "email":
                            "carol@example.com",
                    }
                ],
                "reply_to": [],
            },
            received_at=newer,
        )


        state, processed = (
            refresh_recipient_directory(
                user=self.user
            )
        )


        self.assertEqual(
            processed,
            2,
        )

        self.assertEqual(
            state.indexed_message_count,
            2,
        )


        self.assertFalse(
            RecipientContact.objects
            .filter(
                user=self.user,
                normalized_email=(
                    self.account
                    .email_address
                ),
            )
            .exists()
        )


        alice = (
            RecipientContact.objects
            .get(
                user=self.user,
                normalized_email=(
                    "alice@example.com"
                ),
            )
        )

        bob = (
            RecipientContact.objects
            .get(
                user=self.user,
                normalized_email=(
                    "bob@example.com"
                ),
            )
        )

        carol = (
            RecipientContact.objects
            .get(
                user=self.user,
                normalized_email=(
                    "carol@example.com"
                ),
            )
        )


        self.assertEqual(
            alice.message_count,
            2,
        )

        self.assertEqual(
            alice.sent_count,
            1,
        )

        self.assertEqual(
            alice.received_count,
            1,
        )

        self.assertEqual(
            alice.to_count,
            1,
        )

        self.assertEqual(
            alice.reply_to_count,
            1,
        )

        self.assertEqual(
            alice.display_name,
            "Alice Example",
        )

        self.assertEqual(
            alice.first_seen_at,
            older,
        )

        self.assertEqual(
            alice.last_seen_at,
            newer,
        )


        self.assertEqual(
            bob.sent_count,
            1,
        )

        self.assertEqual(
            bob.cc_count,
            1,
        )

        self.assertEqual(
            carol.sent_count,
            1,
        )

        self.assertEqual(
            carol.bcc_count,
            1,
        )


    def test_refresh_is_idempotent(
        self,
    ):
        self.message(
            external_id="idempotent-1",
            direction="inbound",
            sender=(
                "stable@example.com"
            ),
            recipients=(
                self.account
                .email_address
            ),
            sender_meta={
                "name":
                    "Stable Contact",
                "email":
                    "stable@example.com",
            },
            recipient_meta={},
        )


        first_state, first_processed = (
            refresh_recipient_directory(
                user=self.user
            )
        )

        contact = (
            RecipientContact.objects
            .get(
                user=self.user,
                normalized_email=(
                    "stable@example.com"
                ),
            )
        )

        original_message_count = (
            contact.message_count
        )


        second_state, second_processed = (
            refresh_recipient_directory(
                user=self.user
            )
        )


        contact.refresh_from_db()


        self.assertEqual(
            first_processed,
            1,
        )

        self.assertEqual(
            second_processed,
            0,
        )

        self.assertEqual(
            contact.message_count,
            original_message_count,
        )

        self.assertEqual(
            second_state
            .last_indexed_message_id,
            first_state
            .last_indexed_message_id,
        )


    def test_incremental_refresh_only_consumes_new_messages(
        self,
    ):
        first = self.message(
            external_id="incremental-1",
            direction="outbound",
            sender=(
                self.account
                .email_address
            ),
            recipients=(
                "repeat@example.com"
            ),
            sender_meta={
                "email":
                    self.account
                    .email_address,
                "name":
                    "",
            },
            recipient_meta={
                "to": [
                    {
                        "name":
                            "Repeat Contact",
                        "email":
                            "repeat@example.com",
                    }
                ],
                "cc": [],
                "bcc": [],
                "reply_to": [],
            },
        )


        state, processed = (
            refresh_recipient_directory(
                user=self.user
            )
        )


        self.assertEqual(
            processed,
            1,
        )

        self.assertEqual(
            state.last_indexed_message_id,
            first.id,
        )


        second = self.message(
            external_id="incremental-2",
            direction="outbound",
            sender=(
                self.account
                .email_address
            ),
            recipients=(
                "repeat@example.com"
            ),
            sender_meta={
                "email":
                    self.account
                    .email_address,
                "name":
                    "",
            },
            recipient_meta={
                "to": [
                    {
                        "name":
                            "Repeat Contact",
                        "email":
                            "repeat@example.com",
                    }
                ],
                "cc": [],
                "bcc": [],
                "reply_to": [],
            },
            received_at=(
                timezone.now()
                +
                timedelta(
                    minutes=1
                )
            ),
        )


        state, processed = (
            refresh_recipient_directory(
                user=self.user
            )
        )


        contact = (
            RecipientContact.objects
            .get(
                user=self.user,
                normalized_email=(
                    "repeat@example.com"
                ),
            )
        )


        self.assertEqual(
            processed,
            1,
        )

        self.assertEqual(
            state.last_indexed_message_id,
            second.id,
        )

        self.assertEqual(
            state.indexed_message_count,
            2,
        )

        self.assertEqual(
            contact.sent_count,
            2,
        )

        self.assertEqual(
            contact.message_count,
            2,
        )


    def test_legacy_flat_recipient_fallback_is_indexed(
        self,
    ):
        self.message(
            external_id="legacy-flat",
            direction="outbound",
            sender=(
                self.account
                .email_address
            ),
            recipients=(
                "Legacy Person "
                "<legacy@example.com>; "
                + self.account
                .email_address
            ),
            sender_meta={},
            recipient_meta={},
        )


        refresh_recipient_directory(
            user=self.user
        )


        legacy = (
            RecipientContact.objects
            .get(
                user=self.user,
                normalized_email=(
                    "legacy@example.com"
                ),
            )
        )


        self.assertEqual(
            legacy.display_name,
            "Legacy Person",
        )

        self.assertEqual(
            legacy.sent_count,
            1,
        )

        self.assertEqual(
            legacy.to_count,
            1,
        )


        self.assertFalse(
            RecipientContact.objects
            .filter(
                user=self.user,
                normalized_email=(
                    self.account
                    .email_address
                ),
            )
            .exists()
        )


    def test_suggestion_api_is_user_scoped_and_ranks_sent_contacts(
        self,
    ):
        for index in range(
            2
        ):
            self.message(
                external_id=(
                    "alice-out-"
                    + str(index)
                ),
                direction="outbound",
                sender=(
                    self.account
                    .email_address
                ),
                recipients=(
                    "alice@example.com"
                ),
                sender_meta={
                    "email":
                        self.account
                        .email_address,
                    "name":
                        "",
                },
                recipient_meta={
                    "to": [
                        {
                            "name":
                                "Alice Example",
                            "email":
                                "alice@example.com",
                        }
                    ],
                    "cc": [],
                    "bcc": [],
                    "reply_to": [],
                },
            )


        self.message(
            external_id="adam-in",
            direction="inbound",
            sender=(
                "adam@example.com"
            ),
            recipients=(
                self.account
                .email_address
            ),
            sender_meta={
                "name":
                    "Adam Example",
                "email":
                    "adam@example.com",
            },
            recipient_meta={},
        )


        other_user = (
            User.objects.create_user(
                email=(
                    "other-user@oneuch.test"
                ),
                password="pass123",
            )
        )

        other_org = (
            Organization.objects.create(
                name="Other Org",
                slug="other-recipient-org",
            )
        )

        OrganizationUser.objects.create(
            user=other_user,
            organization=(
                other_org
            ),
            role="member",
        )

        other_account = (
            EmailAccount.objects.create(
                user=other_user,
                account_type="gmail",
                email_address=(
                    "other@gmail.com"
                ),
                is_active=True,
            )
        )


        self.message(
            external_id="other-private",
            direction="outbound",
            sender=(
                other_account
                .email_address
            ),
            recipients=(
                "attacker@example.com"
            ),
            sender_meta={
                "email":
                    other_account
                    .email_address,
                "name":
                    "",
            },
            recipient_meta={
                "to": [
                    {
                        "name":
                            "Other Private",
                        "email":
                            "attacker@example.com",
                    }
                ],
                "cc": [],
                "bcc": [],
                "reply_to": [],
            },
            user=other_user,
            organization=(
                other_org
            ),
            account=(
                other_account
            ),
        )


        self.client.force_authenticate(
            user=self.user
        )


        response = (
            self.client.get(
                "/api/inbox/"
                "recipient-suggestions/"
                "?q=a"
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        results = (
            response.data[
                "results"
            ]
        )


        emails = [
            item[
                "email"
            ]
            for item
            in results
        ]


        self.assertGreaterEqual(
            len(
                results
            ),
            2,
        )

        self.assertEqual(
            emails[
                0
            ],
            "alice@example.com",
        )

        self.assertIn(
            "adam@example.com",
            emails,
        )

        self.assertNotIn(
            "attacker@example.com",
            emails,
        )

        self.assertNotIn(
            self.account
            .email_address,
            emails,
        )


        self.assertEqual(
            response.data[
                "refreshed_message_count"
            ],
            3,
        )


    def test_suggestion_service_supports_name_and_email_prefix_search(
        self,
    ):
        self.message(
            external_id="named-contact",
            direction="outbound",
            sender=(
                self.account
                .email_address
            ),
            recipients=(
                "nirav.customer@example.com"
            ),
            sender_meta={
                "email":
                    self.account
                    .email_address,
                "name":
                    "",
            },
            recipient_meta={
                "to": [
                    {
                        "name":
                            "Nirav Customer",
                        "email":
                            "nirav.customer@example.com",
                    }
                ],
                "cc": [],
                "bcc": [],
                "reply_to": [],
            },
        )


        by_name = (
            suggest_recipients(
                user=self.user,
                query="nir",
                limit=10,
            )
        )


        self.assertEqual(
            by_name[
                "results"
            ][0][
                "email"
            ],
            "nirav.customer@example.com",
        )


        by_email = (
            suggest_recipients(
                user=self.user,
                query="nirav.c",
                limit=10,
            )
        )


        self.assertEqual(
            by_email[
                "results"
            ][0][
                "name"
            ],
            "Nirav Customer",
        )


        state = (
            RecipientDirectoryState.objects
            .get(
                user=self.user,
                organization=(
                    self.organization
                ),
            )
        )


        self.assertEqual(
            state.indexed_message_count,
            1,
        )
