from unittest.mock import (
    Mock,
    patch,
)

from uuid import uuid4

from django.test import (
    TestCase,
)

from django.utils import (
    timezone,
)

from accounts.models import (
    User,
)

from email_accounts.models import (
    EmailAccount,
)

from email_accounts.services.imap_convergence import (
    reconcile_imap_inbox_membership,
)

from inbox.models import (
    Conversation,
    InboxMessage,
    Organization,
    OrganizationUser,
)

from inbox.tasks import (
    _pending_mail_intelligence_message_ids,
)


class IMAPInboxMembershipReconciliationTests(
    TestCase
):

    def setUp(
        self,
    ):

        self.user = (
            User.objects.create_user(
                email=(
                    "imap-membership@oneuch.test"
                ),
                password="pass123",
            )
        )


        self.organization = (
            Organization.objects.create(
                name=(
                    "IMAP Membership Workspace"
                ),
                slug=(
                    "imap-membership-"
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
                    "imap-membership@example.com"
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
                    "Synthetic-Membership-Credential"
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
                subject="Membership",
                conversation_key=(
                    "imap-membership-"
                    + uuid4().hex
                ),
                unread_count=1,
            )
        )


    def create_message(
        self,
        *,
        identity,
        folder="inbox",
    ):

        return (
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
                folder=folder,
                direction="inbound",
                external_message_id=(
                    identity
                ),
                sender=(
                    "sender@example.net"
                ),
                recipients=(
                    self.account.email_address
                ),
                subject="Membership",
                body="Body",
                received_at=(
                    timezone.now()
                ),
                is_read=False,
                status="queued",
            )
        )


    def test_missing_rfc_message_is_archived_locally(
        self,
    ):

        identity = (
            "imap-rfc822-"
            + (
                "a"
                *
                64
            )
        )


        message = (
            self.create_message(
                identity=identity
            )
        )


        mail = Mock()


        with (
            patch(
                (
                    "email_accounts.services."
                    "imap_convergence."
                    "_open_imap_mailbox"
                ),
                return_value=mail,
            ),
            patch(
                (
                    "email_accounts.services."
                    "imap_convergence."
                    "_scan_folder_for_identities"
                ),
                return_value={},
            ),
            patch(
                (
                    "email_accounts.services."
                    "imap_convergence."
                    "invalidate_conversation_cache"
                )
            ) as invalidate_mock,
        ):

            result = (
                reconcile_imap_inbox_membership(
                    user=self.user,
                    email_account=(
                        self.account
                    ),
                )
            )


        message.refresh_from_db()

        self.conversation.refresh_from_db()


        self.assertEqual(
            message.folder,
            "archive",
        )


        self.assertEqual(
            result[
                "stale"
            ],
            1,
        )


        self.assertEqual(
            result[
                "updated"
            ],
            1,
        )


        self.assertEqual(
            self.conversation.unread_count,
            0,
        )


        invalidate_mock.assert_called_once_with(
            self.user.id
        )


        mail.logout.assert_called_once()


    def test_present_rfc_message_remains_inbox(
        self,
    ):

        identity = (
            "imap-rfc822-"
            + (
                "b"
                *
                64
            )
        )


        message = (
            self.create_message(
                identity=identity
            )
        )


        mail = Mock()


        with (
            patch(
                (
                    "email_accounts.services."
                    "imap_convergence."
                    "_open_imap_mailbox"
                ),
                return_value=mail,
            ),
            patch(
                (
                    "email_accounts.services."
                    "imap_convergence."
                    "_scan_folder_for_identities"
                ),
                return_value={
                    identity: [
                        "17"
                    ]
                },
            ),
            patch(
                (
                    "email_accounts.services."
                    "imap_convergence."
                    "log_event"
                )
            ) as log_mock,
        ):

            result = (
                reconcile_imap_inbox_membership(
                    user=self.user,
                    email_account=(
                        self.account
                    ),
                )
            )


        message.refresh_from_db()


        self.assertEqual(
            message.folder,
            "inbox",
        )


        self.assertEqual(
            result[
                "present"
            ],
            1,
        )


        self.assertEqual(
            result[
                "stale"
            ],
            0,
        )


        self.assertEqual(
            result[
                "updated"
            ],
            0,
        )


        log_mock.assert_called_once()


        log_args = (
            log_mock
            .call_args
            .args
        )


        log_kwargs = (
            log_mock
            .call_args
            .kwargs
        )


        self.assertEqual(
            log_args[2],
            "imap.inbox_membership.reconciled",
        )


        self.assertEqual(
            log_kwargs[
                "stale_count"
            ],
            0,
        )


        self.assertEqual(
            log_kwargs[
                "updated_count"
            ],
            0,
        )


        self.assertTrue(
            log_kwargs[
                "apply_changes"
            ]
        )


    def test_uid_only_identity_is_fail_safe(
        self,
    ):

        identity = (
            "imap-uid-"
            + (
                "c"
                *
                64
            )
        )


        message = (
            self.create_message(
                identity=identity
            )
        )


        with patch(
            (
                "email_accounts.services."
                "imap_convergence."
                "_open_imap_mailbox"
            )
        ) as open_mock:

            result = (
                reconcile_imap_inbox_membership(
                    user=self.user,
                    email_account=(
                        self.account
                    ),
                )
            )


        message.refresh_from_db()


        self.assertEqual(
            message.folder,
            "inbox",
        )


        self.assertEqual(
            result[
                "skipped_unstable"
            ],
            1,
        )


        self.assertEqual(
            result[
                "updated"
            ],
            0,
        )


        open_mock.assert_not_called()


    def test_dry_run_does_not_archive(
        self,
    ):

        identity = (
            "imap-rfc822-"
            + (
                "d"
                *
                64
            )
        )


        message = (
            self.create_message(
                identity=identity
            )
        )


        mail = Mock()


        with (
            patch(
                (
                    "email_accounts.services."
                    "imap_convergence."
                    "_open_imap_mailbox"
                ),
                return_value=mail,
            ),
            patch(
                (
                    "email_accounts.services."
                    "imap_convergence."
                    "_scan_folder_for_identities"
                ),
                return_value={},
            ),
        ):

            result = (
                reconcile_imap_inbox_membership(
                    user=self.user,
                    email_account=(
                        self.account
                    ),
                    apply_changes=False,
                )
            )


        message.refresh_from_db()


        self.assertEqual(
            message.folder,
            "inbox",
        )


        self.assertEqual(
            result[
                "stale"
            ],
            1,
        )


        self.assertEqual(
            result[
                "updated"
            ],
            0,
        )


    def test_archive_is_excluded_from_intelligence(
        self,
    ):

        message = (
            self.create_message(
                identity=(
                    "imap-rfc822-"
                    + (
                        "e"
                        *
                        64
                    )
                ),
                folder="archive",
            )
        )


        message_ids = (
            _pending_mail_intelligence_message_ids(
                account=(
                    self.account
                )
            )
        )


        self.assertNotIn(
            message.id,
            message_ids,
        )
