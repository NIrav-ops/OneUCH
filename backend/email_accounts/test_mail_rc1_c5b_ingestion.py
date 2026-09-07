from datetime import (
    datetime,
    timezone as datetime_timezone,
)

from email.message import (
    EmailMessage,
)

from types import (
    SimpleNamespace,
)

from unittest.mock import (
    Mock,
    patch,
)

from uuid import (
    uuid4,
)

from django.test import (
    TestCase,
)

from accounts.models import (
    User,
)

from email_accounts.models import (
    EmailAccount,
)

from email_accounts.services.imap_smtp import (
    _discover_imap_folders,
    _folder_last_uid,
    _message_identities,
    _message_timestamp,
    _stable_external_message_id,
    _thread_identity,
    fetch_imap_emails,
)

from inbox.models import (
    Conversation,
    InboxMessage,
    Organization,
    OrganizationUser,
)


class FakeIMAP:

    def __init__(
        self,
        *,
        folder_messages=None,
        folder_list=None,
        uidvalidity=None,
    ):
        self.folder_messages = (
            folder_messages
            or {}
        )

        self.folder_list = (
            folder_list
            or [
                (
                    b'(\\HasNoChildren) '
                    b'"/" "INBOX"'
                ),
                (
                    b'(\\HasNoChildren \\Sent) '
                    b'"/" "Sent Items"'
                ),
                (
                    b'(\\HasNoChildren \\Drafts) '
                    b'"/" "Drafts"'
                ),
                (
                    b'(\\HasNoChildren \\Trash) '
                    b'"/" "Trash"'
                ),
            ]
        )

        self.uidvalidity = (
            uidvalidity
            or {
                "INBOX":
                    "777",

                "Sent Items":
                    "888",
            }
        )

        self.selected = None

        self.logged_out = False


    def login(
        self,
        email_address,
        password,
    ):
        return (
            "OK",
            [
                b"authenticated"
            ],
        )


    def list(
        self,
    ):
        return (
            "OK",
            self.folder_list,
        )


    @staticmethod
    def _decode_mailbox(
        mailbox,
    ):
        source = str(
            mailbox
            or ""
        )

        if (
            source.startswith('"')
            and
            source.endswith('"')
        ):

            source = (
                source[
                    1:-1
                ]
                .replace(
                    '\\"',
                    '"',
                )
                .replace(
                    "\\\\",
                    "\\",
                )
            )

        return source


    def select(
        self,
        mailbox,
    ):
        name = (
            self._decode_mailbox(
                mailbox
            )
        )

        if (
            name
            not in
            self.folder_messages
        ):
            return (
                "NO",
                [],
            )

        self.selected = (
            name
        )

        return (
            "OK",
            [
                b"1"
            ],
        )


    def response(
        self,
        name,
    ):
        if (
            name
            !=
            "UIDVALIDITY"
        ):

            return (
                name,
                [],
            )

        return (
            "UIDVALIDITY",
            [
                str(
                    self.uidvalidity.get(
                        self.selected,
                        "1",
                    )
                ).encode(
                    "ascii"
                )
            ],
        )


    def uid(
        self,
        command,
        *args,
    ):
        command = (
            str(
                command
            )
            .lower()
        )

        messages = (
            self.folder_messages.get(
                self.selected,
                {},
            )
        )


        if command == "search":

            values = [
                str(uid).encode(
                    "ascii"
                )
                for uid in sorted(
                    messages,
                    key=lambda item:
                        int(item),
                )
            ]

            return (
                "OK",
                [
                    b" ".join(
                        values
                    )
                ],
            )


        if command == "fetch":

            uid = args[0]

            uid_text = (
                uid.decode(
                    "ascii"
                )
                if isinstance(
                    uid,
                    bytes,
                )
                else
                str(uid)
            )

            item = (
                messages[
                    uid_text
                ]
            )

            flags = (
                item.get(
                    "flags",
                    "",
                )
            )

            internaldate = (
                item.get(
                    "internaldate",
                    (
                        "07-Sep-2026 "
                        "10:00:00 +0000"
                    ),
                )
            )

            metadata = (
                (
                    uid_text
                    + " (UID "
                    + uid_text
                    + " FLAGS ("
                    + flags
                    + ') INTERNALDATE "'
                    + internaldate
                    + '")'
                )
                .encode(
                    "utf-8"
                )
            )

            return (
                "OK",
                [
                    (
                        metadata,
                        item[
                            "raw"
                        ],
                    )
                ],
            )


        raise AssertionError(
            "Unexpected UID command: "
            + command
        )


    def logout(
        self,
    ):
        self.logged_out = True

        return (
            "BYE",
            [
                b"logout"
            ],
        )


class MailRC1C5BIngestionTests(
    TestCase
):

    PASSWORD = (
        "C5B-User-Password-74129"
    )

    MAIL_CREDENTIAL = (
        "C5B-Synthetic-Mail-Credential-85193"
    )


    def setUp(
        self,
    ):
        self.user = (
            User.objects.create_user(
                email=(
                    "mail-c5b@oneuch.test"
                ),
                password=(
                    self.PASSWORD
                ),
            )
        )

        self.organization = (
            Organization.objects.create(
                name="C5B Workspace",
                slug=(
                    "mail-c5b-"
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
                    "owner@example.com"
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
                    self.MAIL_CREDENTIAL
                ),
                credential_status="active",
                is_active=True,
            )
        )


    def build_message(
        self,
        *,
        message_id=None,
        in_reply_to=None,
        references=None,
        sender=(
            "Alice Example "
            "<alice@example.net>"
        ),
        to=(
            "Owner <owner@example.com>"
        ),
        cc=None,
        bcc=None,
        reply_to=None,
        subject="C5B subject",
        date=(
            "Sun, 06 Sep 2026 "
            "10:00:00 +0000"
        ),
        body="C5B message body",
    ):
        message = (
            EmailMessage()
        )

        if message_id:

            message[
                "Message-ID"
            ] = message_id

        if in_reply_to:

            message[
                "In-Reply-To"
            ] = in_reply_to

        if references:

            message[
                "References"
            ] = references

        if sender:

            message[
                "From"
            ] = sender

        if to:

            message[
                "To"
            ] = to

        if cc:

            message[
                "Cc"
            ] = cc

        if bcc:

            message[
                "Bcc"
            ] = bcc

        if reply_to:

            message[
                "Reply-To"
            ] = reply_to

        if date:

            message[
                "Date"
            ] = date

        message[
            "Subject"
        ] = subject

        message.set_content(
            body
        )

        return message


    def sync_with_fake(
        self,
        fake,
    ):
        processor = Mock()

        endpoint = (
            SimpleNamespace(
                host=(
                    "imap.example.com"
                ),
                port=993,
            )
        )

        with (
            patch(
                (
                    "email_accounts.services."
                    "imap_smtp."
                    "validate_mailbox_endpoint"
                ),
                return_value=(
                    endpoint
                ),
            ),
            patch(
                (
                    "email_accounts.services."
                    "imap_smtp."
                    "_PinnedIMAP4SSL"
                ),
                return_value=(
                    fake
                ),
            ),
            patch(
                (
                    "email_accounts.services."
                    "imap_smtp."
                    "update_sync_status"
                )
            ),
            patch(
                (
                    "email_accounts.services."
                    "imap_smtp."
                    "invalidate_conversation_cache"
                )
            ),
            patch(
                (
                    "email_accounts.services."
                    "imap_smtp."
                    "MessageProcessor"
                )
            ) as processor_factory,
            patch(
                (
                    "email_accounts.services."
                    "imap_smtp."
                    "get_channel_layer"
                )
            ),
            patch(
                (
                    "email_accounts.services."
                    "imap_smtp."
                    "async_to_sync"
                ),
                return_value=(
                    lambda *args, **kwargs:
                        None
                ),
            ),
        ):

            processor_factory.return_value = (
                processor
            )

            result = (
                fetch_imap_emails(
                    user=self.user,
                    email_account=(
                        self.account
                    ),
                    password=(
                        self.MAIL_CREDENTIAL
                    ),
                )
            )

        return (
            result,
            processor,
        )


    # ========================================================
    # 1. \Sent discovery wins and Draft/Trash never enter the
    # governed ingestion set.
    # ========================================================

    def test_folder_discovery_uses_special_sent_and_only_returns_inbox_sent(
        self,
    ):
        folders = (
            _discover_imap_folders(
                [
                    (
                        b'(\\HasNoChildren) '
                        b'"/" "INBOX"'
                    ),
                    (
                        b'(\\HasNoChildren \\Sent) '
                        b'"/" "Archive/Sent Items"'
                    ),
                    (
                        b'(\\HasNoChildren \\Drafts) '
                        b'"/" "Drafts"'
                    ),
                    (
                        b'(\\HasNoChildren \\Trash) '
                        b'"/" "Trash"'
                    ),
                ]
            )
        )

        self.assertEqual(
            [
                item[
                    "folder_key"
                ]
                for item in folders
            ],
            [
                "inbox",
                "sent",
            ],
        )

        self.assertEqual(
            folders[
                1
            ][
                "folder_name"
            ],
            "Archive/Sent Items",
        )


    # ========================================================
    # 2. Exact conservative Sent aliases remain available for
    # servers without RFC SPECIAL-USE flags.
    # ========================================================

    def test_folder_discovery_uses_conservative_sent_alias_fallback(
        self,
    ):
        folders = (
            _discover_imap_folders(
                [
                    (
                        b'(\\HasNoChildren) '
                        b'"/" "INBOX"'
                    ),
                    (
                        b'(\\HasNoChildren) '
                        b'"/" "[Provider]/Sent Mail"'
                    ),
                ]
            )
        )

        self.assertEqual(
            folders[
                1
            ][
                "folder_name"
            ],
            "[Provider]/Sent Mail",
        )


    # ========================================================
    # 3. C5B never silently claims a complete Inbox/Sent sync
    # if the Sent folder cannot be identified.
    # ========================================================

    def test_folder_discovery_rejects_missing_sent_folder(
        self,
    ):
        with self.assertRaisesRegex(
            RuntimeError,
            "Unable to discover IMAP Sent folder",
        ):

            _discover_imap_folders(
                [
                    (
                        b'(\\HasNoChildren) '
                        b'"/" "INBOX"'
                    ),
                    (
                        b'(\\HasNoChildren \\Drafts) '
                        b'"/" "Drafts"'
                    ),
                ]
            )


    # ========================================================
    # 4. RFC Date becomes the local source timestamp rather
    # than timezone.now().
    # ========================================================

    def test_rfc_date_is_preserved_as_source_timestamp(
        self,
    ):
        message = (
            self.build_message(
                date=(
                    "Sun, 06 Sep 2026 "
                    "10:11:12 +0000"
                )
            )
        )

        value = (
            _message_timestamp(
                message,
                (
                    '10 (INTERNALDATE '
                    '"06-Sep-2026 '
                    '11:00:00 +0000")'
                ),
            )
        )

        self.assertEqual(
            value,
            datetime(
                2026,
                9,
                6,
                10,
                11,
                12,
                tzinfo=(
                    datetime_timezone.utc
                ),
            ),
        )


    # ========================================================
    # 5. INTERNALDATE is the safe provider fallback when an RFC
    # Date header is absent or unusable.
    # ========================================================

    def test_internaldate_is_timestamp_fallback(
        self,
    ):
        message = (
            self.build_message(
                date=None
            )
        )

        value = (
            _message_timestamp(
                message,
                (
                    '10 (INTERNALDATE '
                    '"06-Sep-2026 '
                    '11:12:13 +0000")'
                ),
            )
        )

        self.assertEqual(
            value,
            datetime(
                2026,
                9,
                6,
                11,
                12,
                13,
                tzinfo=(
                    datetime_timezone.utc
                ),
            ),
        )


    # ========================================================
    # 6. IMAP addresses use the same sender_meta /
    # recipient_meta shape as Gmail and Microsoft.
    # ========================================================

    def test_structured_sender_and_recipient_metadata(
        self,
    ):
        message = (
            self.build_message(
                sender=(
                    "Alice Example "
                    "<ALICE@example.net>"
                ),
                to=(
                    "Owner <OWNER@example.com>"
                ),
                cc=(
                    "Bob <BOB@example.net>"
                ),
                bcc=(
                    "Hidden "
                    "<HIDDEN@example.net>"
                ),
                reply_to=(
                    "Replies "
                    "<reply@example.net>"
                ),
            )
        )

        (
            sender_meta,
            recipient_meta,
        ) = (
            _message_identities(
                message
            )
        )

        self.assertEqual(
            sender_meta[
                "email"
            ],
            "alice@example.net",
        )

        self.assertEqual(
            recipient_meta[
                "to"
            ][0][
                "email"
            ],
            "owner@example.com",
        )

        self.assertEqual(
            recipient_meta[
                "cc"
            ][0][
                "email"
            ],
            "bob@example.net",
        )

        self.assertEqual(
            recipient_meta[
                "bcc"
            ][0][
                "email"
            ],
            "hidden@example.net",
        )

        self.assertEqual(
            recipient_meta[
                "reply_to"
            ][0][
                "email"
            ],
            "reply@example.net",
        )


    # ========================================================
    # 7. RFC References root is the conversation identity.
    # ========================================================

    def test_references_root_controls_thread_identity(
        self,
    ):
        message = (
            self.build_message(
                message_id=(
                    "<child@example.net>"
                ),
                in_reply_to=(
                    "<parent@example.net>"
                ),
                references=(
                    "<root@example.net> "
                    "<parent@example.net>"
                ),
            )
        )

        self.assertEqual(
            _thread_identity(
                message,
                fallback="fallback",
            ),
            "<root@example.net>",
        )


    # ========================================================
    # 8. The same RFC Message-ID is deduplicated independently
    # of folder UID or UIDVALIDITY.
    # ========================================================

    def test_message_id_dedup_is_independent_of_uid(
        self,
    ):
        message = (
            self.build_message(
                message_id=(
                    "<stable@example.net>"
                )
            )
        )

        first = (
            _stable_external_message_id(
                email_account=(
                    self.account
                ),
                folder_key="inbox",
                uid="10",
                uidvalidity="111",
                message=message,
            )
        )

        second = (
            _stable_external_message_id(
                email_account=(
                    self.account
                ),
                folder_key="sent",
                uid="999",
                uidvalidity="222",
                message=message,
            )
        )

        self.assertEqual(
            first,
            second,
        )


    # ========================================================
    # 9. UIDVALIDITY change invalidates an old incremental UID
    # cursor instead of skipping potentially new provider data.
    # ========================================================

    def test_uidvalidity_change_resets_incremental_cursor(
        self,
    ):
        state = {
            "inbox":
                900,

            "_uidvalidity": {
                "inbox":
                    "111",
            },
        }

        self.assertEqual(
            _folder_last_uid(
                state,
                folder_key="inbox",
                uidvalidity="222",
            ),
            0,
        )


    # ========================================================
    # 10. End-to-end mocked provider sync materializes only
    # Inbox/Sent with timestamps, metadata, RFC threading,
    # cursor state and MessageProcessor handoff.
    # ========================================================

    def test_governed_imap_sync_materializes_normalized_inbox_and_sent(
        self,
    ):
        root = (
            self.build_message(
                message_id=(
                    "<thread-root@example.net>"
                ),
                sender=(
                    "Alice "
                    "<alice@example.net>"
                ),
                to=(
                    "Owner "
                    "<owner@example.com>"
                ),
                subject=(
                    "Project update"
                ),
                date=(
                    "Sun, 06 Sep 2026 "
                    "10:00:00 +0000"
                ),
                body=(
                    "Initial project update."
                ),
            )
        )

        reply = (
            self.build_message(
                message_id=(
                    "<thread-reply@example.net>"
                ),
                in_reply_to=(
                    "<thread-root@example.net>"
                ),
                references=(
                    "<thread-root@example.net>"
                ),
                sender=(
                    "Owner "
                    "<owner@example.com>"
                ),
                to=(
                    "Alice "
                    "<alice@example.net>"
                ),
                cc=(
                    "Bob "
                    "<bob@example.net>"
                ),
                subject=(
                    "Re: Project update"
                ),
                date=(
                    "Sun, 06 Sep 2026 "
                    "11:00:00 +0000"
                ),
                body=(
                    "Thanks for the update."
                ),
            )
        )

        draft = (
            self.build_message(
                message_id=(
                    "<draft@example.net>"
                )
            )
        )

        trash = (
            self.build_message(
                message_id=(
                    "<trash@example.net>"
                )
            )
        )


        fake = (
            FakeIMAP(
                folder_messages={
                    "INBOX": {
                        "10": {
                            "raw":
                                root.as_bytes(),

                            "flags":
                                "",
                        },
                    },

                    "Sent Items": {
                        "20": {
                            "raw":
                                reply.as_bytes(),

                            "flags":
                                (
                                    "\\Seen "
                                    "\\Flagged"
                                ),
                        },
                    },

                    "Drafts": {
                        "30": {
                            "raw":
                                draft.as_bytes(),
                        },
                    },

                    "Trash": {
                        "40": {
                            "raw":
                                trash.as_bytes(),
                        },
                    },
                }
            )
        )


        result, processor = (
            self.sync_with_fake(
                fake
            )
        )


        messages = (
            InboxMessage.objects
            .filter(
                email_account=(
                    self.account
                )
            )
            .order_by(
                "received_at"
            )
        )


        self.assertEqual(
            messages.count(),
            2,
        )

        self.assertEqual(
            set(
                messages.values_list(
                    "folder",
                    flat=True,
                )
            ),
            {
                "inbox",
                "sent",
            },
        )


        inbound = (
            messages.get(
                folder="inbox"
            )
        )

        outbound = (
            messages.get(
                folder="sent"
            )
        )


        self.assertEqual(
            inbound.received_at,
            datetime(
                2026,
                9,
                6,
                10,
                0,
                0,
                tzinfo=(
                    datetime_timezone.utc
                ),
            ),
        )

        self.assertEqual(
            inbound.sender_meta[
                "email"
            ],
            "alice@example.net",
        )

        self.assertEqual(
            inbound.recipient_meta[
                "to"
            ][0][
                "email"
            ],
            "owner@example.com",
        )

        self.assertEqual(
            outbound.recipient_meta[
                "cc"
            ][0][
                "email"
            ],
            "bob@example.net",
        )

        self.assertEqual(
            inbound.conversation_id,
            outbound.conversation_id,
        )

        self.assertEqual(
            outbound.in_reply_to,
            "<thread-root@example.net>",
        )

        self.assertEqual(
            outbound.direction,
            "outbound",
        )

        self.assertEqual(
            outbound.status,
            "sent",
        )

        self.assertTrue(
            outbound.is_starred
        )


        self.account.refresh_from_db()


        self.assertIsNotNone(
            self.account
            .history_sync_completed_at
        )

        self.assertEqual(
            self.account
            .last_synced_uids[
                "inbox"
            ],
            10,
        )

        self.assertEqual(
            self.account
            .last_synced_uids[
                "sent"
            ],
            20,
        )

        self.assertEqual(
            (
                self.account
                .last_synced_uids[
                    "_uidvalidity"
                ][
                    "inbox"
                ]
            ),
            "777",
        )


        self.assertEqual(
            processor
            .process_message
            .call_count,
            2,
        )


        self.assertEqual(
            result[
                "created"
            ],
            2,
        )

        self.assertEqual(
            result[
                "failed"
            ],
            0,
        )

        self.assertTrue(
            result[
                "history_complete"
            ]
        )


    # ========================================================
    # 11. Legacy folder_UID rows are upgraded in place instead
    # of duplicated by the new stable Message-ID identity.
    # ========================================================

    def test_legacy_uid_identity_is_upgraded_without_duplicate(
        self,
    ):
        raw_message = (
            self.build_message(
                message_id=(
                    "<legacy-upgrade@example.net>"
                ),
                sender=(
                    "Legacy Sender "
                    "<legacy@example.net>"
                ),
                date=(
                    "Sun, 06 Sep 2026 "
                    "12:00:00 +0000"
                ),
            )
        )


        legacy_conversation = (
            Conversation.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                email_account=(
                    self.account
                ),
                conversation_key=(
                    "legacy-imap-"
                    + uuid4().hex
                ),
                subject=(
                    "Legacy thread"
                ),
            )
        )


        legacy = (
            InboxMessage.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                email_account=(
                    self.account
                ),
                conversation=(
                    legacy_conversation
                ),
                platform="imap",
                folder="inbox",
                direction="inbound",
                external_message_id=(
                    "inbox_10"
                ),
                sender=(
                    "legacy@example.net"
                ),
                recipients=(
                    "owner@example.com"
                ),
                subject=(
                    "Legacy thread"
                ),
                body="legacy",
                received_at=(
                    datetime(
                        2026,
                        9,
                        6,
                        12,
                        0,
                        0,
                        tzinfo=(
                            datetime_timezone.utc
                        ),
                    )
                ),
            )
        )


        fake = (
            FakeIMAP(
                folder_messages={
                    "INBOX": {
                        "10": {
                            "raw":
                                raw_message
                                .as_bytes(),

                            "flags":
                                "\\Seen",
                        },
                    },

                    "Sent Items":
                        {},
                }
            )
        )


        result, _ = (
            self.sync_with_fake(
                fake
            )
        )


        self.assertEqual(
            InboxMessage.objects
            .filter(
                email_account=(
                    self.account
                )
            )
            .count(),
            1,
        )


        legacy.refresh_from_db()


        self.assertTrue(
            legacy
            .external_message_id
            .startswith(
                "imap-rfc822-"
            )
        )

        self.assertEqual(
            result[
                "upgraded"
            ],
            1,
        )


    # ========================================================
    # 12. A failed message must not advance the folder cursor or
    # falsely mark initial history complete.
    # ========================================================

    def test_message_failure_does_not_advance_cursor_or_complete_history(
        self,
    ):
        malformed = (
            self.build_message(
                message_id=(
                    "<bad-c5b@example.net>"
                ),
                sender=None,
                date=(
                    "Sun, 06 Sep 2026 "
                    "13:00:00 +0000"
                ),
            )
        )


        fake = (
            FakeIMAP(
                folder_messages={
                    "INBOX": {
                        "10": {
                            "raw":
                                malformed
                                .as_bytes(),

                            "flags":
                                "",
                        },
                    },

                    "Sent Items":
                        {},
                }
            )
        )


        with self.assertRaisesRegex(
            RuntimeError,
            "partial sync failure",
        ):

            self.sync_with_fake(
                fake
            )


        self.account.refresh_from_db()


        self.assertNotIn(
            "inbox",
            self.account
            .last_synced_uids,
        )

        self.assertIsNone(
            self.account
            .history_sync_completed_at
        )
