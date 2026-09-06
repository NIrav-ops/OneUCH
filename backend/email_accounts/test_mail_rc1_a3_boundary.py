from datetime import (
    timedelta,
)

from pathlib import Path

from unittest.mock import (
    patch,
)

from uuid import (
    uuid4,
)

from django.core.exceptions import (
    FieldDoesNotExist,
)

from django.db import (
    models,
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

from accounts.models import (
    User,
)

from email_accounts.models import (
    EmailAccount,
)

from inbox.models import (
    InboxMessage,
    Organization,
    OrganizationUser,
)

from inbox.services.outbound_idempotency import (
    OutboundIdempotencyUnavailable,
)

from inbox.tasks import (
    send_email_task,
    sync_email_account,
)


ROOT = Path(
    r"D:\UnifiedMessenger\unified-comm-hub"
)


class MailRC1A3BoundaryTests(
    TestCase
):

    PASSWORD = (
        "A3-Test-Password-Only-93471"
    )

    def setUp(
        self,
    ):
        self.user = (
            User.objects.create_user(
                email=(
                    "mail-a3@oneuch.test"
                ),
                password=(
                    self.PASSWORD
                ),
            )
        )

        self.org = (
            Organization.objects.create(
                name="A3 Workspace",
                slug=(
                    "mail-a3-"
                    + uuid4().hex
                ),
            )
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=self.org,
            role="owner",
        )

        self.client = (
            APIClient()
        )

        self.client.force_authenticate(
            user=self.user
        )

    def account_kwargs(
        self,
        *,
        account_type="imap",
        email_address=(
            "mailbox@oneuch.test"
        ),
        organization=None,
        **extra,
    ):
        kwargs = {
            "user":
                self.user,

            "account_type":
                account_type,

            "email_address":
                email_address,

            **extra,
        }

        field_names = {
            field.name
            for field
            in EmailAccount._meta.fields
        }

        if (
            "organization"
            in field_names
        ):
            kwargs[
                "organization"
            ] = (
                organization
                or
                self.org
            )

        return kwargs

    def create_account(
        self,
        **kwargs,
    ):
        return (
            EmailAccount.objects.create(
                **self.account_kwargs(
                    **kwargs
                )
            )
        )

    # ========================================================
    # POSITIVE CONTROL 1
    # Existing credential lifecycle method remains useful.
    # ========================================================

    def test_valid_credential_lifecycle_control(
        self,
    ):
        account = self.create_account(
            credential_status="active",
            credential_expires_at=(
                timezone.now()
                + timedelta(hours=1)
            ),
        )

        self.assertTrue(
            account.is_credential_valid()
        )

    # ========================================================
    # POSITIVE CONTROL 2
    # Existing list API must not expose mailbox secrets/config.
    # ========================================================

    def test_mailbox_list_does_not_expose_secret_fields_control(
        self,
    ):
        self.create_account(
            account_type="imap",
            smtp_password=(
                "synthetic-secret"
            ),
            imap_server=(
                "imap.example.test"
            ),
            imap_port=993,
            smtp_server=(
                "smtp.example.test"
            ),
            smtp_port=465,
        )

        response = self.client.get(
            "/api/email/email-accounts/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

        item = response.data[0]

        for forbidden in (
            "smtp_password",
            "credential_ciphertext",
            "imap_server",
            "imap_port",
            "smtp_server",
            "smtp_port",
        ):

            self.assertNotIn(
                forbidden,
                item,
            )

    # ========================================================
    # RED 1
    # EmailAccount itself must carry workspace ownership.
    # ========================================================

    def test_email_account_has_explicit_workspace_key(
        self,
    ):
        field_names = {
            field.name
            for field
            in EmailAccount._meta.fields
        }

        self.assertIn(
            "organization",
            field_names,
        )

        try:
            field = (
                EmailAccount._meta
                .get_field(
                    "organization"
                )
            )

        except FieldDoesNotExist:

            self.fail(
                "EmailAccount has no organization field"
            )

        self.assertIsInstance(
            field,
            models.ForeignKey,
        )

    # ========================================================
    # RED 2
    # Plaintext smtp_password must be replaced by an encrypted
    # credential-at-rest storage contract.
    # ========================================================

    def test_mailbox_credential_is_not_plaintext_model_field(
        self,
    ):
        field_names = {
            field.name
            for field
            in EmailAccount._meta.fields
        }

        self.assertNotIn(
            "smtp_password",
            field_names,
        )

        self.assertIn(
            "credential_ciphertext",
            field_names,
        )

    # ========================================================
    # RED 3
    # Same workspace/provider/address must be model-unique.
    # ========================================================

    def test_workspace_mailbox_uniqueness_is_declared(
        self,
    ):
        expected = {
            "organization",
            "account_type",
            "email_address",
        }

        constraint_fields = []

        for constraint in (
            EmailAccount
            ._meta
            .constraints
        ):

            fields = getattr(
                constraint,
                "fields",
                None,
            )

            if fields:
                constraint_fields.append(
                    set(
                        fields
                    )
                )

        self.assertIn(
            expected,
            constraint_fields,
        )

    # ========================================================
    # RED 4
    # Invalid IMAP credentials must stop before provider I/O.
    # ========================================================

    def test_imap_sync_rejects_invalid_credential_before_provider_call(
        self,
    ):
        account = self.create_account(
            account_type="imap",
            smtp_password=(
                "synthetic-imap-secret"
            ),
            credential_status=(
                "reauth_required"
            ),
            imap_server=(
                "imap.example.test"
            ),
            imap_port=993,
        )

        with patch(
            "inbox.tasks.acquire_sync_lock",
            return_value="synthetic-lock",
        ):

            with patch(
                "inbox.tasks.release_sync_lock"
            ):

                with patch(
                    "inbox.tasks.fetch_imap_emails"
                ) as provider:

                    with patch(
                        "inbox.tasks.analyze_new_approvals.delay"
                    ):

                        result = (
                            sync_email_account.run(
                                account.id
                            )
                        )

        provider.assert_not_called()

        self.assertEqual(
            result.get(
                "status"
            ),
            "skipped",
        )

        self.assertEqual(
            result.get(
                "reason"
            ),
            "invalid_credential",
        )

    # ========================================================
    # RED 5
    # A user match alone is insufficient. Message and mailbox
    # must belong to the same workspace before provider I/O.
    # ========================================================

    def test_async_send_rejects_cross_workspace_message_before_provider_call(
        self,
    ):
        other_org = (
            Organization.objects.create(
                name=(
                    "Poison Workspace"
                ),
                slug=(
                    "mail-a3-poison-"
                    + uuid4().hex
                ),
            )
        )

        account = self.create_account(
            account_type="imap",
            organization=self.org,
            smtp_password=(
                "synthetic-smtp-secret"
            ),
            credential_status="active",
        )

        message = (
            InboxMessage.objects.create(
                user=self.user,
                organization=other_org,
                email_account=account,
                platform="imap",
                direction="outbound",
                external_message_id=(
                    "pending-"
                    + uuid4().hex
                ),
                sender=(
                    account.email_address
                ),
                recipients=(
                    "recipient@oneuch.test"
                ),
                subject="A3 poison send",
                body="Do not deliver",
                received_at=(
                    timezone.now()
                ),
                is_read=True,
                status="queued",
            )
        )

        with patch(
            (
                "inbox.tasks."
                "get_outbound_intent_for_message"
            ),
            side_effect=(
                OutboundIdempotencyUnavailable(
                    "synthetic unavailable"
                )
            ),
        ):

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

                result = (
                    send_email_task.run(
                        account.id,
                        (
                            "recipient@"
                            "oneuch.test"
                        ),
                        "A3 poison send",
                        "Do not deliver",
                        message.id,
                    )
                )

        provider.assert_not_called()

        message.refresh_from_db()

        self.assertNotEqual(
            message.status,
            "sent",
        )

        self.assertNotEqual(
            result.get(
                "status"
            )
            if isinstance(
                result,
                dict,
            )
            else None,
            "sent",
        )

    # ========================================================
    # RED 6
    # Legacy SMTP endpoint must never select Gmail/Outlook just
    # because it happens to be the first active mailbox.
    # ========================================================

    def test_legacy_send_rejects_non_imap_account_selection(
        self,
    ):
        self.create_account(
            account_type="gmail",
            email_address=(
                "gmail@oneuch.test"
            ),
            smtp_password=(
                "synthetic-not-for-smtp"
            ),
            credential_status="active",
        )

        with patch(
            (
                "email_accounts.views."
                "send_email_task.delay"
            )
        ) as queued:

            response = self.client.post(
                "/api/email/send/",
                {
                    "to":
                        "recipient@oneuch.test",

                    "subject":
                        "A3 provider boundary",

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

    # ========================================================
    # RED 7
    # IMAP account with invalid lifecycle state must not queue.
    # ========================================================

    def test_legacy_send_rejects_invalid_imap_credential(
        self,
    ):
        self.create_account(
            account_type="imap",
            smtp_password=(
                "synthetic-invalid-secret"
            ),
            credential_status=(
                "reauth_required"
            ),
            smtp_server=(
                "smtp.example.test"
            ),
            smtp_port=465,
        )

        with patch(
            (
                "email_accounts.views."
                "send_email_task.delay"
            )
        ) as queued:

            response = self.client.post(
                "/api/email/send/",
                {
                    "to":
                        "recipient@oneuch.test",

                    "subject":
                        "A3 credential boundary",

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

    # ========================================================
    # RED 8
    # IMAP runtime must not print provider/message failures or
    # persist raw exception text into sync-health records.
    # ========================================================

    def test_imap_runtime_does_not_print_or_persist_raw_exception_text(
        self,
    ):
        source = (
            ROOT
            .joinpath(
                (
                    "backend/email_accounts/"
                    "services/imap_smtp.py"
                )
            )
            .read_text(
                encoding="utf-8"
            )
        )

        self.assertNotRegex(
            source,
            r"\bprint\s*\(",
        )

        compact = (
            source.replace(
                " ",
                ""
            )
            .replace(
                "\n",
                ""
            )
        )

        self.assertNotIn(
            "error_message=str(e)",
            compact,
        )
