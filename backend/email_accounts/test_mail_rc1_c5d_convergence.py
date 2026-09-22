from email.message import EmailMessage
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from email_accounts.models import EmailAccount

from email_accounts.services.imap_convergence import (
    IMAPConvergenceError,
    _discover_imap_trash_folder,
    reconcile_imap_trash,
    set_imap_conversation_read,
    set_imap_conversation_star,
    trash_imap_conversation,
)

from email_accounts.services.imap_smtp import (
    _stable_external_message_id,
)

from inbox.models import (
    Conversation,
    InboxMessage,
    Organization,
    OrganizationUser,
)


class FakeConvergenceIMAP:

    def __init__(
        self,
        *,
        folder_messages=None,
        uidvalidity=None,
    ):
        self.folder_messages = (
            folder_messages
            or {
                "INBOX": {},
                "Sent": {},
                "Trash": {},
            }
        )

        self.uidvalidity = (
            uidvalidity
            or {
                "INBOX": "111",
                "Sent": "222",
                "Trash": "333",
            }
        )

        self.selected = None
        self.move_calls = []
        self.store_calls = []
        self.fetch_queries = []
        self.logged_out = False


    @staticmethod
    def _decode_mailbox(mailbox):
        value = str(
            mailbox or ""
        )

        if (
            value.startswith('"')
            and value.endswith('"')
        ):
            value = value[1:-1]

            value = value.replace(
                '\\"',
                '"',
            )

            value = value.replace(
                "\\\\",
                "\\",
            )

        return value


    def login(
        self,
        email_address,
        password,
    ):
        return (
            "OK",
            [b"authenticated"],
        )


    def capability(self):
        return (
            "OK",
            [
                (
                    b"IMAP4rev1 MOVE "
                    b"UIDPLUS SPECIAL-USE"
                )
            ],
        )


    def list(self):
        return (
            "OK",
            [
                (
                    b'(\\HasNoChildren) '
                    b'"/" "INBOX"'
                ),
                (
                    b'(\\HasNoChildren \\Sent) '
                    b'"/" "Sent"'
                ),
                (
                    b'(\\HasNoChildren \\Trash) '
                    b'"/" "Trash"'
                ),
            ],
        )


    def select(
        self,
        mailbox,
    ):
        name = (
            self._decode_mailbox(
                mailbox
            )
        )

        if name not in self.folder_messages:
            return (
                "NO",
                [],
            )

        self.selected = name

        return (
            "OK",
            [
                str(
                    len(
                        self.folder_messages[
                            name
                        ]
                    )
                ).encode("ascii")
            ],
        )


    def response(
        self,
        name,
    ):
        if name != "UIDVALIDITY":
            return (
                name,
                [],
            )

        return (
            "UIDVALIDITY",
            [
                self.uidvalidity[
                    self.selected
                ].encode("ascii")
            ],
        )


    def uid(
        self,
        command,
        *args,
    ):
        command = (
            str(command)
            .lower()
        )

        messages = (
            self.folder_messages[
                self.selected
            ]
        )


        if command == "search":

            header_search = (
                len(args) >= 4
                and
                str(args[1]).casefold()
                ==
                "header"
                and
                str(args[2]).casefold()
                ==
                "message-id"
            )

            if header_search:

                target = (
                    str(
                        args[3]
                        or ""
                    )
                    .strip()
                )

                if (
                    len(target) >= 2
                    and
                    target.startswith('"')
                    and
                    target.endswith('"')
                ):
                    target = (
                        target[1:-1]
                        .replace(
                            '\\"',
                            '"',
                        )
                        .replace(
                            "\\\\",
                            "\\",
                        )
                    )

                target = (
                    target.casefold()
                )

                matching = [
                    uid
                    for uid, item
                    in messages.items()
                    if (
                        target
                        in
                        str(
                            item.get(
                                "message_id",
                                "",
                            )
                        )
                        .casefold()
                    )
                ]

            else:

                matching = list(
                    messages
                )

            values = [
                str(uid).encode("ascii")
                for uid in sorted(
                    matching,
                    key=lambda item:
                        int(item),
                )
            ]

            return (
                "OK",
                [
                    b" ".join(values)
                ],
            )


        if command == "fetch":

            raw_uid_set = args[0]

            uid_set = (
                raw_uid_set.decode(
                    "ascii"
                )
                if isinstance(
                    raw_uid_set,
                    bytes,
                )
                else str(
                    raw_uid_set
                )
            )

            uid_values = [
                value.strip()
                for value in (
                    uid_set.split(",")
                )
                if value.strip()
            ]

            self.fetch_queries.append(
                str(args[1])
            )

            response = []

            for uid in uid_values:

                item = messages[
                    uid
                ]

                header = (
                    (
                        "Message-ID: "
                        + item["message_id"]
                        + "\r\n\r\n"
                    )
                    .encode("utf-8")
                )

                metadata = (
                    (
                        uid
                        + " (UID "
                        + uid
                        + ")"
                    )
                    .encode("ascii")
                )

                response.append(
                    (
                        metadata,
                        header,
                    )
                )

            return (
                "OK",
                response,
            )


        if command == "store":

            uid = str(
                args[0]
            )

            operation = str(
                args[1]
            )

            flag = str(
                args[2]
            )

            self.store_calls.append(
                (
                    self.selected,
                    uid,
                    operation,
                    flag,
                )
            )

            return (
                "OK",
                [b"stored"],
            )


        if command == "move":

            uid = str(
                args[0]
            )

            destination = (
                self._decode_mailbox(
                    args[1]
                )
            )

            self.move_calls.append(
                (
                    self.selected,
                    uid,
                    destination,
                )
            )

            item = messages.pop(
                uid
            )

            destination_messages = (
                self.folder_messages[
                    destination
                ]
            )

            existing = [
                int(value)
                for value
                in destination_messages
            ]

            next_uid = str(
                (
                    max(existing)
                    if existing
                    else 900
                )
                + 1
            )

            destination_messages[
                next_uid
            ] = item

            return (
                "OK",
                [b"moved"],
            )


        raise AssertionError(
            "Unexpected UID command: "
            + command
        )


    def logout(self):
        self.logged_out = True

        return (
            "BYE",
            [b"logout"],
        )


class MailRC1C5DConvergenceTests(
    TestCase
):

    MAIL_CREDENTIAL = (
        "Synthetic-C5D-Credential-92741"
    )


    def setUp(self):
        self.user = (
            User.objects.create_user(
                email=(
                    "mail-c5d@oneuch.test"
                ),
                password="pass123",
            )
        )

        self.organization = (
            Organization.objects.create(
                name="C5D Workspace",
                slug=(
                    "mail-c5d-"
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


    def stable_identity(
        self,
        message_id,
    ):
        message = EmailMessage()

        message[
            "Message-ID"
        ] = message_id

        return (
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


    def make_message(
        self,
        *,
        message_id,
        folder="inbox",
    ):
        conversation = (
            Conversation.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                email_account=(
                    self.account
                ),
                subject="C5D",
                conversation_key=(
                    "c5d-"
                    + uuid4().hex
                ),
            )
        )

        message = (
            InboxMessage.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                email_account=(
                    self.account
                ),
                conversation=(
                    conversation
                ),
                platform="imap",
                folder=folder,
                direction="inbound",
                external_message_id=(
                    self.stable_identity(
                        message_id
                    )
                ),
                sender=(
                    "sender@example.net"
                ),
                recipients=(
                    self.account.email_address
                ),
                subject="C5D",
                body="Body",
                received_at=(
                    timezone.now()
                ),
                status="queued",
            )
        )

        return (
            conversation,
            message,
        )


    def provider_patches(
        self,
        fake,
    ):
        endpoint = (
            SimpleNamespace(
                host="imap.example.com",
                port=993,
            )
        )

        return (
            patch(
                (
                    "email_accounts.services."
                    "imap_convergence."
                    "validate_mailbox_endpoint"
                ),
                return_value=endpoint,
            ),
            patch(
                (
                    "email_accounts.services."
                    "imap_convergence."
                    "_PinnedIMAP4SSL"
                ),
                return_value=fake,
            ),
            patch(
                (
                    "email_accounts.services."
                    "imap_convergence."
                    "invalidate_conversation_cache"
                )
            ),
        )


    def test_trash_discovery_prefers_special_use(
        self,
    ):
        trash = (
            _discover_imap_trash_folder(
                [
                    (
                        b'(\\HasNoChildren) '
                        b'"/" "INBOX"'
                    ),
                    (
                        b'(\\HasNoChildren \\Trash) '
                        b'"/" "Deleted Items"'
                    ),
                ]
            )
        )


        self.assertIsNotNone(
            trash
        )

        self.assertEqual(
            trash[
                "folder_key"
            ],
            "trash",
        )

        self.assertEqual(
            trash[
                "folder_name"
            ],
            "Deleted Items",
        )


    def test_provider_trash_reconciles_existing_local_message(
        self,
    ):
        conversation, message = (
            self.make_message(
                message_id=(
                    "<provider-trash@example.net>"
                )
            )
        )


        fake = (
            FakeConvergenceIMAP(
                folder_messages={
                    "INBOX":
                        {},

                    "Sent":
                        {},

                    "Trash": {
                        "50": {
                            "message_id":
                                (
                                    "<provider-trash@example.net>"
                                ),
                        },
                    },
                }
            )
        )


        (
            endpoint_patch,
            client_patch,
            cache_patch,
        ) = (
            self.provider_patches(
                fake
            )
        )


        with (
            endpoint_patch,
            client_patch,
            cache_patch,
        ):

            result = (
                reconcile_imap_trash(
                    user=self.user,
                    email_account=(
                        self.account
                    ),
                )
            )


        message.refresh_from_db()

        conversation.refresh_from_db()

        self.account.refresh_from_db()


        self.assertEqual(
            result[
                "status"
            ],
            "completed",
        )

        self.assertEqual(
            result[
                "processed"
            ],
            1,
        )

        self.assertEqual(
            result[
                "matched"
            ],
            1,
        )


        self.assertEqual(
            message.folder,
            "trash",
        )


        self.assertEqual(
            self.account
            .last_synced_uids[
                "trash"
            ],
            50,
        )


        self.assertEqual(
            self.account
            .last_synced_uids[
                "_uidvalidity"
            ][
                "trash"
            ],
            "333",
        )


        self.assertEqual(
            fake.move_calls,
            [],
        )


        self.assertTrue(
            fake.fetch_queries
        )


        self.assertTrue(
            all(
                "HEADER.FIELDS"
                in query
                for query
                in fake.fetch_queries
            )
        )


        self.assertTrue(
            fake.logged_out
        )


    def test_invalid_message_id_fetch_retries_once(
        self,
    ):
        conversation, message = (
            self.make_message(
                message_id=(
                    "<retry-trash@example.net>"
                )
            )
        )

        fake = (
            FakeConvergenceIMAP(
                folder_messages={
                    "INBOX": {},
                    "Sent": {},
                    "Trash": {
                        "50": {
                            "message_id": (
                                "<retry-trash@example.net>"
                            ),
                        },
                    },
                }
            )
        )

        original_uid = fake.uid
        state = {
            "invalid_returned": False,
        }

        def flaky_uid(
            command,
            *args,
        ):
            if (
                str(command).lower()
                == "fetch"
                and not state[
                    "invalid_returned"
                ]
            ):
                state[
                    "invalid_returned"
                ] = True

                return (
                    "OK",
                    [None],
                )

            return original_uid(
                command,
                *args,
            )

        (
            endpoint_patch,
            client_patch,
            cache_patch,
        ) = self.provider_patches(
            fake
        )

        with (
            endpoint_patch,
            client_patch,
            cache_patch,
            patch.object(
                fake,
                "uid",
                side_effect=flaky_uid,
            ),
        ):
            result = (
                reconcile_imap_trash(
                    user=self.user,
                    email_account=(
                        self.account
                    ),
                )
            )

        message.refresh_from_db()

        self.assertTrue(
            state[
                "invalid_returned"
            ]
        )

        self.assertEqual(
            result["status"],
            "completed",
        )

        self.assertEqual(
            result["matched"],
            1,
        )

        self.assertEqual(
            message.folder,
            "trash",
        )

        self.assertTrue(
            fake.logged_out
        )


    def test_persistent_invalid_message_id_fetch_fails_closed(
        self,
    ):
        conversation, message = (
            self.make_message(
                message_id=(
                    "<invalid-trash@example.net>"
                )
            )
        )

        fake = (
            FakeConvergenceIMAP(
                folder_messages={
                    "INBOX": {},
                    "Sent": {},
                    "Trash": {
                        "50": {
                            "message_id": (
                                "<invalid-trash@example.net>"
                            ),
                        },
                    },
                }
            )
        )

        original_uid = fake.uid

        def invalid_uid(
            command,
            *args,
        ):
            if (
                str(command).lower()
                == "fetch"
            ):
                return (
                    "OK",
                    [None],
                )

            return original_uid(
                command,
                *args,
            )

        (
            endpoint_patch,
            client_patch,
            cache_patch,
        ) = self.provider_patches(
            fake
        )

        with (
            endpoint_patch,
            client_patch,
            cache_patch,
            patch.object(
                fake,
                "uid",
                side_effect=invalid_uid,
            ),
        ):
            with self.assertRaisesRegex(
                IMAPConvergenceError,
                (
                    "Message-ID header "
                    "response is invalid"
                ),
            ):
                reconcile_imap_trash(
                    user=self.user,
                    email_account=(
                        self.account
                    ),
                )

        message.refresh_from_db()
        self.account.refresh_from_db()

        self.assertEqual(
            message.folder,
            "inbox",
        )

        state = (
            self.account.last_synced_uids
            if isinstance(
                self.account.last_synced_uids,
                dict,
            )
            else {}
        )

        self.assertNotIn(
            "trash",
            state,
        )

        self.assertTrue(
            fake.logged_out
        )


    def test_provider_trash_active_copy_check_does_not_fetch_unrelated_active_messages(
        self,
    ):
        conversation, message = (
            self.make_message(
                message_id=(
                    "<scale-trash@example.net>"
                )
            )
        )

        inbox_messages = {
            str(uid): {
                "message_id":
                    (
                        "<unrelated-"
                        + str(uid)
                        + "@example.net>"
                    ),
            }
            for uid in range(
                1,
                101,
            )
        }

        fake = (
            FakeConvergenceIMAP(
                folder_messages={
                    "INBOX":
                        inbox_messages,

                    "Sent":
                        {},

                    "Trash": {
                        "500": {
                            "message_id":
                                (
                                    "<scale-trash@example.net>"
                                ),
                        },
                    },
                }
            )
        )

        (
            endpoint_patch,
            client_patch,
            cache_patch,
        ) = (
            self.provider_patches(
                fake
            )
        )

        with (
            endpoint_patch,
            client_patch,
            cache_patch,
        ):
            result = (
                reconcile_imap_trash(
                    user=self.user,
                    email_account=(
                        self.account
                    ),
                )
            )

        message.refresh_from_db()

        self.assertEqual(
            result["status"],
            "completed",
        )

        self.assertEqual(
            result["matched"],
            1,
        )

        self.assertEqual(
            message.folder,
            "trash",
        )

        # One FETCH is required for the new Trash candidate.
        # The 100 unrelated active Inbox messages must not be
        # header-fetched individually.
        self.assertEqual(
            len(
                fake.fetch_queries
            ),
            1,
        )


    def test_oneuch_delete_uses_provider_message_id_search(
        self,
    ):
        conversation, message = (
            self.make_message(
                message_id=(
                    "<interactive-batch@example.net>"
                )
            )
        )


        message.external_conversation_id = (
            "<interactive-batch@example.net>"
        )

        message.save(
            update_fields=[
                "external_conversation_id",
            ]
        )

        inbox_messages = {
            str(uid): {
                "message_id":
                    (
                        "<unrelated-delete-"
                        + str(uid)
                        + "@example.net>"
                    ),
            }
            for uid in range(
                1,
                101,
            )
        }

        inbox_messages["150"] = {
            "message_id":
                "<interactive-batch@example.net>",
        }

        fake = (
            FakeConvergenceIMAP(
                folder_messages={
                    "INBOX":
                        inbox_messages,

                    "Sent":
                        {},

                    "Trash":
                        {},
                }
            )
        )

        (
            endpoint_patch,
            client_patch,
            cache_patch,
        ) = self.provider_patches(
            fake
        )

        with (
            endpoint_patch,
            client_patch,
            cache_patch,
        ):
            result = (
                trash_imap_conversation(
                    conversation=(
                        conversation
                    ),
                    user=self.user,
                )
            )

        message.refresh_from_db()

        self.assertEqual(
            result["moved"],
            1,
        )

        self.assertEqual(
            message.folder,
            "trash",
        )

        self.assertEqual(
            len(
                fake.fetch_queries
            ),
            1,
        )

        self.assertEqual(
            len(
                fake.move_calls
            ),
            1,
        )


    def test_oneuch_delete_falls_back_when_provider_message_id_search_misses(
        self,
    ):
        conversation, message = (
            self.make_message(
                message_id=(
                    "<provider-header-miss@example.net>"
                )
            )
        )

        # Make direct Message-ID recovery valid.
        message.external_conversation_id = (
            "<provider-header-miss@example.net>"
        )

        message.sender = (
            "fallback-sender@example.net"
        )

        message.subject = (
            "Provider Header Search Miss"
        )

        message.save(
            update_fields=[
                "external_conversation_id",
                "sender",
                "subject",
            ]
        )

        fake = (
            FakeConvergenceIMAP(
                folder_messages={
                    "INBOX": {
                        "150": {
                            "message_id":
                                (
                                    "<provider-header-miss@example.net>"
                                ),
                        },
                    },

                    "Sent":
                        {},

                    "Trash":
                        {},
                }
            )
        )

        search_calls = []

        original_uid = (
            fake.uid
        )

        def provider_uid(
            command,
            *args,
        ):
            if (
                str(command)
                .casefold()
                ==
                "search"
            ):

                search_calls.append(
                    args
                )

                header_search = (
                    len(args) >= 4
                    and
                    str(args[1]).casefold()
                    ==
                    "header"
                    and
                    str(args[2]).casefold()
                    ==
                    "message-id"
                )

                # Model the live provider behavior:
                # HEADER Message-ID returns no hit even though
                # the target message really exists.
                if header_search:

                    return (
                        "OK",
                        [b""],
                    )

            return original_uid(
                command,
                *args,
            )

        fake.uid = provider_uid

        (
            endpoint_patch,
            client_patch,
            cache_patch,
        ) = self.provider_patches(
            fake
        )

        with (
            endpoint_patch,
            client_patch,
            cache_patch,
        ):
            result = (
                trash_imap_conversation(
                    conversation=(
                        conversation
                    ),
                    user=self.user,
                )
            )

        message.refresh_from_db()

        self.assertEqual(
            result["moved"],
            1,
        )

        self.assertEqual(
            message.folder,
            "trash",
        )

        normalized_searches = [
            [
                str(value)
                .casefold()
                for value in call
            ]
            for call in search_calls
        ]

        self.assertTrue(
            any(
                "header" in call
                and
                "message-id" in call
                for call in normalized_searches
            )
        )

        self.assertTrue(
            any(
                "on" in call
                and
                "from" in call
                for call in normalized_searches
            )
        )

        self.assertEqual(
            len(
                fake.fetch_queries
            ),
            1,
        )

        self.assertEqual(
            len(
                fake.move_calls
            ),
            1,
        )


    def test_oneuch_delete_uses_bounded_historical_provider_search(
        self,
    ):
        conversation, message = (
            self.make_message(
                message_id=(
                    "<historical-delete@example.net>"
                )
            )
        )

        # Deliberately make the stored thread identity differ
        # from this message's own RFC Message-ID. This forces
        # the compatibility lookup rather than direct
        # Message-ID recovery.
        message.external_conversation_id = (
            "<historical-thread-root@example.net>"
        )

        message.sender = (
            "historical-sender@example.net"
        )

        message.subject = (
            "Historical Provider Delete"
        )

        message.save(
            update_fields=[
                "external_conversation_id",
                "sender",
                "subject",
            ]
        )

        fake = (
            FakeConvergenceIMAP(
                folder_messages={
                    "INBOX": {
                        "150": {
                            "message_id":
                                (
                                    "<historical-delete@example.net>"
                                ),
                        },
                    },

                    "Sent":
                        {},

                    "Trash":
                        {},
                }
            )
        )

        search_calls = []

        original_uid = (
            fake.uid
        )

        def recording_uid(
            command,
            *args,
        ):
            if (
                str(command)
                .casefold()
                ==
                "search"
            ):
                search_calls.append(
                    args
                )

            return original_uid(
                command,
                *args,
            )

        fake.uid = recording_uid

        (
            endpoint_patch,
            client_patch,
            cache_patch,
        ) = self.provider_patches(
            fake
        )

        with (
            endpoint_patch,
            client_patch,
            cache_patch,
        ):
            result = (
                trash_imap_conversation(
                    conversation=(
                        conversation
                    ),
                    user=self.user,
                )
            )

        message.refresh_from_db()

        self.assertEqual(
            result["moved"],
            1,
        )

        self.assertEqual(
            message.folder,
            "trash",
        )

        normalized_searches = [
            [
                str(value)
                .casefold()
                for value in call
            ]
            for call in search_calls
        ]

        self.assertTrue(
            any(
                "on" in call
                and
                "from" in call
                and
                "subject" in call
                for call in normalized_searches
            )
        )

        self.assertFalse(
            any(
                "header" in call
                and
                "message-id" in call
                for call in normalized_searches
            )
        )

        self.assertEqual(
            len(
                fake.fetch_queries
            ),
            1,
        )

        self.assertEqual(
            len(
                fake.move_calls
            ),
            1,
        )


    def test_oneuch_delete_uses_uid_move_and_updates_local_state(
        self,
    ):
        conversation, message = (
            self.make_message(
                message_id=(
                    "<oneuch-trash@example.net>"
                )
            )
        )


        fake = (
            FakeConvergenceIMAP(
                folder_messages={
                    "INBOX": {
                        "10": {
                            "message_id":
                                (
                                    "<oneuch-trash@example.net>"
                                ),
                        },
                    },

                    "Sent":
                        {},

                    "Trash":
                        {},
                }
            )
        )


        (
            endpoint_patch,
            client_patch,
            cache_patch,
        ) = (
            self.provider_patches(
                fake
            )
        )


        with (
            endpoint_patch,
            client_patch,
            cache_patch,
            patch(
                (
                    "email_accounts.services."
                    "imap_convergence."
                    "acquire_sync_lock"
                ),
                return_value="test-lock",
            ) as acquire_mock,
            patch(
                (
                    "email_accounts.services."
                    "imap_convergence."
                    "release_sync_lock"
                )
            ) as release_mock,
        ):

            result = (
                trash_imap_conversation(
                    conversation=(
                        conversation
                    ),
                    user=self.user,
                )
            )


        message.refresh_from_db()

        conversation.refresh_from_db()


        self.assertEqual(
            result[
                "status"
            ],
            "completed",
        )

        self.assertEqual(
            result[
                "updated"
            ],
            1,
        )

        self.assertEqual(
            result[
                "moved"
            ],
            1,
        )


        self.assertEqual(
            message.folder,
            "trash",
        )


        self.assertEqual(
            fake.move_calls,
            [
                (
                    "INBOX",
                    "10",
                    "Trash",
                )
            ],
        )


        acquire_mock.assert_called_once_with(
            self.account.id
        )

        release_mock.assert_called_once_with(
            "test-lock"
        )


        self.assertTrue(
            fake.logged_out
        )


    def test_oneuch_delete_fails_closed_when_sync_lock_busy(
        self,
    ):
        conversation, message = (
            self.make_message(
                message_id=(
                    "<lock-busy@example.net>"
                )
            )
        )


        with (
            patch(
                (
                    "email_accounts.services."
                    "imap_convergence."
                    "acquire_sync_lock"
                ),
                return_value=None,
            ) as acquire_mock,
            patch(
                (
                    "email_accounts.services."
                    "imap_convergence."
                    "_open_imap_mailbox"
                )
            ) as open_mock,
            patch(
                (
                    "email_accounts.services."
                    "imap_convergence."
                    "release_sync_lock"
                )
            ) as release_mock,
        ):

            with self.assertRaisesRegex(
                RuntimeError,
                "currently synchronizing",
            ):

                trash_imap_conversation(
                    conversation=(
                        conversation
                    ),
                    user=self.user,
                )


        message.refresh_from_db()


        self.assertEqual(
            message.folder,
            "inbox",
        )


        acquire_mock.assert_called_once_with(
            self.account.id
        )

        open_mock.assert_not_called()

        release_mock.assert_not_called()


    def test_trash_copy_does_not_hide_active_provider_copy(
        self,
    ):
        conversation, message = (
            self.make_message(
                message_id=(
                    "<active-and-trash@example.net>"
                )
            )
        )


        fake = (
            FakeConvergenceIMAP(
                folder_messages={
                    "INBOX": {
                        "10": {
                            "message_id":
                                (
                                    "<active-and-trash@example.net>"
                                ),
                        },
                    },

                    "Sent":
                        {},

                    "Trash": {
                        "50": {
                            "message_id":
                                (
                                    "<active-and-trash@example.net>"
                                ),
                        },
                    },
                }
            )
        )


        (
            endpoint_patch,
            client_patch,
            cache_patch,
        ) = (
            self.provider_patches(
                fake
            )
        )


        with (
            endpoint_patch,
            client_patch,
            cache_patch,
        ):

            result = (
                reconcile_imap_trash(
                    user=self.user,
                    email_account=(
                        self.account
                    ),
                )
            )


        message.refresh_from_db()
        self.account.refresh_from_db()


        self.assertEqual(
            result[
                "status"
            ],
            "completed",
        )

        self.assertEqual(
            result[
                "processed"
            ],
            1,
        )

        self.assertEqual(
            result[
                "matched"
            ],
            0,
        )


        self.assertEqual(
            message.folder,
            "inbox",
        )


        self.assertEqual(
            self.account
            .last_synced_uids[
                "trash"
            ],
            50,
        )


        self.assertEqual(
            fake.move_calls,
            [],
        )


        self.assertTrue(
            fake.logged_out
        )

    def test_imap_read_unread_converges_seen_flag_and_local_state(
        self,
    ):
        conversation, message = (
            self.make_message(
                message_id=(
                    "<imap-read-state@example.net>"
                )
            )
        )


        fake = (
            FakeConvergenceIMAP(
                folder_messages={
                    "INBOX": {
                        "10": {
                            "message_id":
                                "<imap-read-state@example.net>",
                        },
                    },
                    "Sent": {},
                    "Trash": {},
                }
            )
        )


        (
            endpoint_patch,
            client_patch,
            cache_patch,
        ) = self.provider_patches(
            fake
        )


        with (
            endpoint_patch,
            client_patch,
            cache_patch,
            patch(
                (
                    "email_accounts.services."
                    "imap_convergence."
                    "acquire_sync_lock"
                ),
                return_value="flag-lock",
            ),
            patch(
                (
                    "email_accounts.services."
                    "imap_convergence."
                    "release_sync_lock"
                ),
            ),
        ):

            result = (
                set_imap_conversation_read(
                    conversation=conversation,
                    user=self.user,
                    is_read=True,
                )
            )


            message.refresh_from_db()
            conversation.refresh_from_db()


            self.assertTrue(
                message.is_read
            )

            self.assertEqual(
                conversation.unread_count,
                0,
            )

            self.assertEqual(
                result["updated"],
                1,
            )


            set_imap_conversation_read(
                conversation=conversation,
                user=self.user,
                is_read=False,
            )


        message.refresh_from_db()
        conversation.refresh_from_db()


        self.assertFalse(
            message.is_read
        )

        self.assertEqual(
            conversation.unread_count,
            1,
        )


        self.assertEqual(
            fake.store_calls,
            [
                (
                    "INBOX",
                    "10",
                    "+FLAGS.SILENT",
                    r"(\Seen)",
                ),
                (
                    "INBOX",
                    "10",
                    "-FLAGS.SILENT",
                    r"(\Seen)",
                ),
            ],
        )


    def test_imap_star_unstar_converges_flagged_and_local_state(
        self,
    ):
        conversation, message = (
            self.make_message(
                message_id=(
                    "<imap-star-state@example.net>"
                )
            )
        )


        fake = (
            FakeConvergenceIMAP(
                folder_messages={
                    "INBOX": {
                        "11": {
                            "message_id":
                                "<imap-star-state@example.net>",
                        },
                    },
                    "Sent": {},
                    "Trash": {},
                }
            )
        )


        (
            endpoint_patch,
            client_patch,
            cache_patch,
        ) = self.provider_patches(
            fake
        )


        with (
            endpoint_patch,
            client_patch,
            cache_patch,
            patch(
                (
                    "email_accounts.services."
                    "imap_convergence."
                    "acquire_sync_lock"
                ),
                return_value="flag-lock",
            ),
            patch(
                (
                    "email_accounts.services."
                    "imap_convergence."
                    "release_sync_lock"
                ),
            ),
        ):

            set_imap_conversation_star(
                conversation=conversation,
                user=self.user,
                is_starred=True,
            )


            message.refresh_from_db()
            conversation.refresh_from_db()


            self.assertTrue(
                message.is_starred
            )

            self.assertTrue(
                conversation.is_starred
            )


            set_imap_conversation_star(
                conversation=conversation,
                user=self.user,
                is_starred=False,
            )


        message.refresh_from_db()
        conversation.refresh_from_db()


        self.assertFalse(
            message.is_starred
        )

        self.assertFalse(
            conversation.is_starred
        )


        self.assertEqual(
            fake.store_calls,
            [
                (
                    "INBOX",
                    "11",
                    "+FLAGS.SILENT",
                    r"(\Flagged)",
                ),
                (
                    "INBOX",
                    "11",
                    "-FLAGS.SILENT",
                    r"(\Flagged)",
                ),
            ],
        )

    def test_imap_flag_mutation_does_not_require_background_sync_lock(
        self,
    ):
        conversation, message = (
            self.make_message(
                message_id=(
                    "<interactive-no-sync-lock@example.net>"
                )
            )
        )


        fake = (
            FakeConvergenceIMAP(
                folder_messages={
                    "INBOX": {
                        "21": {
                            "message_id":
                                (
                                    "<interactive-no-sync-lock@example.net>"
                                ),
                        },
                    },
                    "Sent": {},
                    "Trash": {},
                }
            )
        )


        (
            endpoint_patch,
            client_patch,
            cache_patch,
        ) = self.provider_patches(
            fake
        )


        with (
            endpoint_patch,
            client_patch,
            cache_patch,
            patch(
                (
                    "email_accounts.services."
                    "imap_convergence."
                    "acquire_sync_lock"
                ),
                return_value=None,
            ) as acquire_mock,
        ):

            result = (
                set_imap_conversation_star(
                    conversation=(
                        conversation
                    ),
                    user=self.user,
                    is_starred=True,
                )
            )


        message.refresh_from_db()


        self.assertEqual(
            result["status"],
            "completed",
        )

        self.assertTrue(
            message.is_starred
        )

        acquire_mock.assert_not_called()


        self.assertEqual(
            fake.store_calls,
            [
                (
                    "INBOX",
                    "21",
                    "+FLAGS.SILENT",
                    r"(\Flagged)",
                ),
            ],
        )


    def test_imap_flag_mutation_falls_back_to_exact_identity_scan(
        self,
    ):
        conversation, message = (
            self.make_message(
                message_id=(
                    "<interactive-scan-fallback@example.net>"
                )
            )
        )


        target_identity = (
            message.external_message_id
        )


        fake = (
            FakeConvergenceIMAP(
                folder_messages={
                    "INBOX": {
                        "22": {
                            "message_id":
                                (
                                    "<interactive-scan-fallback@example.net>"
                                ),
                        },
                    },
                    "Sent": {},
                    "Trash": {},
                }
            )
        )


        (
            endpoint_patch,
            client_patch,
            cache_patch,
        ) = self.provider_patches(
            fake
        )


        def scan_result(
            **kwargs,
        ):

            if (
                kwargs["folder_key"]
                ==
                "inbox"
            ):

                return {
                    target_identity:
                        ["22"]
                }


            return {}


        with (
            endpoint_patch,
            client_patch,
            cache_patch,
            patch(
                (
                    "email_accounts.services."
                    "imap_convergence."
                    "_search_folder_for_local_messages"
                ),
                side_effect=lambda **kwargs: {},
            ),
            patch(
                (
                    "email_accounts.services."
                    "imap_convergence."
                    "_scan_folder_for_identities"
                ),
                side_effect=(
                    scan_result
                ),
            ) as scan_mock,
        ):

            result = (
                set_imap_conversation_read(
                    conversation=(
                        conversation
                    ),
                    user=self.user,
                    is_read=True,
                )
            )


        message.refresh_from_db()


        self.assertEqual(
            result["status"],
            "completed",
        )

        self.assertTrue(
            message.is_read
        )

        self.assertGreaterEqual(
            scan_mock.call_count,
            1,
        )


        self.assertEqual(
            fake.store_calls,
            [
                (
                    "INBOX",
                    "22",
                    "+FLAGS.SILENT",
                    r"(\Seen)",
                ),
            ],
        )

    def test_trash_reconciliation_backfills_before_existing_cursor_once(
        self,
    ):
        conversation, message = (
            self.make_message(
                message_id=(
                    "<historical-provider-trash@example.net>"
                )
            )
        )


        self.account.last_synced_uids = {
            "trash":
                900,

            "_uidvalidity": {
                "trash":
                    "333",
            },
        }

        self.account.save(
            update_fields=[
                "last_synced_uids",
            ]
        )


        fake = (
            FakeConvergenceIMAP(
                folder_messages={
                    "INBOX": {},

                    "Sent": {},

                    "Trash": {
                        "50": {
                            "message_id":
                                (
                                    "<historical-provider-trash@example.net>"
                                ),
                        },
                    },
                }
            )
        )


        (
            endpoint_patch,
            client_patch,
            cache_patch,
        ) = self.provider_patches(
            fake
        )


        observed_last_uids = []


        def historical_search(
            mail,
            *,
            last_uid,
            cutoff,
        ):

            observed_last_uids.append(
                last_uid
            )


            # Historical backfill must ignore the existing 900
            # cursor for this one reconciliation cycle.
            if last_uid == 0:

                return [
                    b"50"
                ]


            return []


        with (
            endpoint_patch,
            client_patch,
            cache_patch,
            patch(
                (
                    "email_accounts.services."
                    "imap_convergence."
                    "_search_folder_uids"
                ),
                side_effect=(
                    historical_search
                ),
            ),
        ):

            result = (
                reconcile_imap_trash(
                    user=self.user,
                    email_account=(
                        self.account
                    ),
                )
            )


        message.refresh_from_db()

        self.account.refresh_from_db()


        self.assertEqual(
            observed_last_uids,
            [0],
        )


        self.assertEqual(
            result["matched"],
            1,
        )


        self.assertEqual(
            message.folder,
            "trash",
        )


        # The old incremental cursor must never regress.
        self.assertEqual(
            self.account
            .last_synced_uids[
                "trash"
            ],
            900,
        )


        self.assertEqual(
            self.account
            .last_synced_uids[
                "_trash_reconciliation_version"
            ],
            1,
        )


        # The second pass is incremental again.
        fake_second = (
            FakeConvergenceIMAP(
                folder_messages={
                    "INBOX": {},
                    "Sent": {},
                    "Trash": {},
                }
            )
        )


        (
            endpoint_patch,
            client_patch,
            cache_patch,
        ) = self.provider_patches(
            fake_second
        )


        observed_second = []


        def incremental_search(
            mail,
            *,
            last_uid,
            cutoff,
        ):

            observed_second.append(
                last_uid
            )

            return []


        with (
            endpoint_patch,
            client_patch,
            cache_patch,
            patch(
                (
                    "email_accounts.services."
                    "imap_convergence."
                    "_search_folder_uids"
                ),
                side_effect=(
                    incremental_search
                ),
            ),
        ):

            reconcile_imap_trash(
                user=self.user,
                email_account=(
                    self.account
                ),
            )


        self.assertEqual(
            observed_second,
            [900],
        )

