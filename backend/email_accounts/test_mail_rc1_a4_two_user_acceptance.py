from unittest.mock import patch
from uuid import uuid4

from celery.exceptions import Retry
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from email_accounts.models import EmailAccount
from inbox.models import InboxMessage, Organization, OrganizationUser
from inbox.tasks import send_email_task


class MailRC1A4TwoUserTenantAcceptanceTests(TestCase):
    PASSWORD = "A4-Two-User-Test-Password-93471"

    def setUp(self):
        self.user_a = User.objects.create_user(
            email="mail-a4-user-a@oneuch.test",
            password=self.PASSWORD,
        )
        self.user_b = User.objects.create_user(
            email="mail-a4-user-b@oneuch.test",
            password=self.PASSWORD,
        )

        self.org_a = Organization.objects.create(
            name="A4 Workspace A",
            slug="mail-a4-a-" + uuid4().hex,
        )
        self.org_b = Organization.objects.create(
            name="A4 Workspace B",
            slug="mail-a4-b-" + uuid4().hex,
        )

        OrganizationUser.objects.create(
            user=self.user_a,
            organization=self.org_a,
            role="owner",
        )
        OrganizationUser.objects.create(
            user=self.user_b,
            organization=self.org_b,
            role="owner",
        )

        self.gmail_a = EmailAccount.objects.create(
            user=self.user_a,
            organization=self.org_a,
            account_type="gmail",
            email_address="a4-user-a@gmail.test",
            is_active=True,
        )

        self.gmail_b = EmailAccount.objects.create(
            user=self.user_b,
            organization=self.org_b,
            account_type="gmail",
            email_address="a4-user-b@gmail.test",
            signature_enabled=True,
            signature_text="Workspace B private signature",
            is_active=True,
        )

        self.imap_b = EmailAccount.objects.create(
            user=self.user_b,
            organization=self.org_b,
            account_type="imap",
            email_address="a4-user-b@imap.test",
            smtp_password="synthetic-a4-imap-credential",
            credential_status="active",
            smtp_server="smtp.a4.example.test",
            smtp_port=465,
            is_active=True,
        )

        self.client_a = APIClient()

        self.client_a.force_authenticate(
            user=self.user_a
        )

    def signature_url(
        self,
        account,
    ):
        return (
            "/api/email/mailbox-signature/"
            + str(account.id)
            + "/"
        )

    # ========================================================
    # ACCEPTANCE 1
    # Workspace-scoped uniqueness must permit the same provider
    # address to exist independently in separate workspaces.
    # ========================================================

    def test_same_provider_address_isolated_per_workspace(
        self,
    ):
        shared_address = (
            "shared-mailbox@oneuch.test"
        )

        account_a = EmailAccount.objects.create(
            user=self.user_a,
            organization=self.org_a,
            account_type="outlook",
            email_address=shared_address,
            is_active=True,
        )

        account_b = EmailAccount.objects.create(
            user=self.user_b,
            organization=self.org_b,
            account_type="outlook",
            email_address=shared_address,
            is_active=True,
        )

        self.assertNotEqual(
            account_a.id,
            account_b.id,
        )

        self.assertEqual(
            EmailAccount.objects.filter(
                account_type="outlook",
                email_address=shared_address,
            ).count(),
            2,
        )

        self.assertEqual(
            account_a.organization_id,
            self.org_a.id,
        )

        self.assertEqual(
            account_b.organization_id,
            self.org_b.id,
        )

    # ========================================================
    # ACCEPTANCE 2
    # User A cannot bind a mailbox to User B's workspace.
    # ========================================================

    def test_model_rejects_cross_workspace_owner_binding(
        self,
    ):
        with self.assertRaisesRegex(
            ValidationError,
            "Mailbox workspace ownership mismatch",
        ):
            EmailAccount.objects.create(
                user=self.user_a,
                organization=self.org_b,
                account_type="gmail",
                email_address=(
                    "poison-a4@gmail.test"
                ),
                is_active=True,
            )

    # ========================================================
    # ACCEPTANCE 3
    # User A mailbox inventory must never expose User B rows.
    # ========================================================

    def test_mailbox_list_isolated_between_two_users(
        self,
    ):
        response = self.client_a.get(
            "/api/email/email-accounts/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        visible_ids = {
            item["id"]
            for item
            in response.data
        }

        self.assertEqual(
            visible_ids,
            {
                self.gmail_a.id,
            },
        )

        self.assertNotIn(
            self.gmail_b.id,
            visible_ids,
        )

        self.assertNotIn(
            self.imap_b.id,
            visible_ids,
        )

    # ========================================================
    # ACCEPTANCE 4
    # User A cannot read or alter User B's signature settings.
    # ========================================================

    def test_signature_read_and_write_are_cross_user_isolated(
        self,
    ):
        get_response = (
            self.client_a.get(
                self.signature_url(
                    self.gmail_b
                )
            )
        )

        self.assertEqual(
            get_response.status_code,
            404,
        )

        patch_response = (
            self.client_a.patch(
                self.signature_url(
                    self.gmail_b
                ),
                {
                    "signature_enabled":
                        True,

                    "signature_text":
                        "Attacker overwrite",
                },
                format="json",
            )
        )

        self.assertEqual(
            patch_response.status_code,
            404,
        )

        self.gmail_b.refresh_from_db()

        self.assertTrue(
            self.gmail_b.signature_enabled
        )

        self.assertEqual(
            self.gmail_b.signature_text,
            (
                "Workspace B private signature"
            ),
        )

    # ========================================================
    # ACCEPTANCE 5
    # User A's adoption projection must never leak User B's
    # mailbox identity.
    # ========================================================

    def test_adoption_projection_does_not_leak_other_user_mailbox(
        self,
    ):
        response = self.client_a.get(
            "/api/mail-adoption/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        google = next(
            item
            for item
            in response.data[
                "providers"
            ]
            if (
                item["provider"]
                ==
                "google"
            )
        )

        self.assertNotEqual(
            google.get(
                "account_id"
            ),
            self.gmail_b.id,
        )

        self.assertNotEqual(
            google.get(
                "email_address"
            ),
            self.gmail_b.email_address,
        )

    # ========================================================
    # ACCEPTANCE 6
    # User A cannot make the legacy send API select User B's
    # otherwise valid IMAP mailbox.
    # ========================================================

    def test_legacy_send_cannot_select_other_users_imap_mailbox(
        self,
    ):
        with patch(
            (
                "email_accounts.views."
                "send_email_task.delay"
            )
        ) as queued:

            response = self.client_a.post(
                "/api/email/send/",
                {
                    "to":
                        "recipient@oneuch.test",

                    "subject":
                        (
                            "A4 cross-user "
                            "send boundary"
                        ),

                    "body":
                        "Must not queue",
                },
                format="json",
            )

        queued.assert_not_called()

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertFalse(
            InboxMessage.objects.filter(
                user=self.user_a,
                direction="outbound",
            ).exists()
        )

    # ========================================================
    # ACCEPTANCE 7
    # A task given User A's message and User B's mailbox must
    # fail closed before provider I/O. A deterministic ownership
    # mismatch must not become a Celery retry/send path.
    # ========================================================

    def test_async_send_blocks_cross_user_mailbox_before_provider_call(
        self,
    ):
        message = (
            InboxMessage.objects.create(
                user=self.user_a,
                organization=self.org_a,
                email_account=self.gmail_a,
                platform="gmail",
                direction="outbound",
                external_message_id=(
                    "a4-pending-"
                    + uuid4().hex
                ),
                sender=(
                    self.gmail_a.email_address
                ),
                recipients=(
                    "recipient@oneuch.test"
                ),
                subject=(
                    "A4 async ownership boundary"
                ),
                body=(
                    "Must not deliver"
                ),
                received_at=(
                    timezone.now()
                ),
                is_read=True,
                status="queued",
            )
        )

        result = None
        retry_error = None

        with patch(
            (
                "inbox.tasks."
                "_deliver_reply_message"
            ),
            return_value={
                "id":
                    "must-not-send"
            },
        ) as provider:

            try:
                result = (
                    send_email_task.run(
                        self.imap_b.id,
                        (
                            "recipient@"
                            "oneuch.test"
                        ),
                        (
                            "A4 async ownership "
                            "boundary"
                        ),
                        (
                            "Must not deliver"
                        ),
                        message.id,
                    )
                )

            except Retry as exc:
                retry_error = exc

        provider.assert_not_called()

        message.refresh_from_db()

        self.assertNotEqual(
            message.status,
            "sent",
        )

        self.assertIsNone(
            retry_error,
            (
                "Cross-user ownership mismatch "
                "must block without Celery retry."
            ),
        )

        self.assertIsInstance(
            result,
            dict,
        )

        self.assertEqual(
            result.get(
                "status"
            ),
            "blocked",
        )
