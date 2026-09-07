from unittest.mock import (
    patch,
)

from uuid import (
    uuid4,
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
    DELIVERY_UNCERTAIN_ERROR_PREFIX,
    retry_failed_messages,
    send_email_task,
)


User = get_user_model()


class MailRC1C5EFinalGovernedMailboxAcceptanceTests(
    TestCase
):

    PASSWORD = (
        "C5E-Governed-Test-93471"
    )


    def setUp(
        self,
    ):
        self.user = (
            User.objects.create_user(
                email=(
                    "mail-c5e@oneuch.test"
                ),
                password=(
                    self.PASSWORD
                ),
            )
        )


        self.organization = (
            Organization.objects.create(
                name="C5E Workspace",
                slug=(
                    "mail-c5e-"
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
                account_type="gmail",
                email_address=(
                    "mail-c5e@gmail.test"
                ),
                credential_status="active",
                is_active=True,
            )
        )


    def message(
        self,
        *,
        account="default",
        direction="outbound",
        is_draft=False,
        status="failed",
        retry_count=1,
        error_reason="Synthetic delivery failure",
        subject=None,
    ):
        if account == "default":
            account = self.account


        return (
            InboxMessage.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                email_account=account,
                platform=(
                    account.account_type
                    if account
                    else "gmail"
                ),
                direction=direction,
                folder=(
                    "drafts"
                    if is_draft
                    else "outbox"
                ),
                external_message_id=(
                    "c5e-"
                    + uuid4().hex
                ),
                sender=(
                    self.account
                    .email_address
                ),
                recipients=(
                    "customer@example.net"
                ),
                recipient_meta={
                    "to": [
                        {
                            "name":
                                "Customer",

                            "email":
                                "customer@example.net",
                        }
                    ],

                    "cc":
                        [],

                    "bcc":
                        [],

                    "reply_to":
                        [],
                },
                subject=(
                    subject
                    or
                    "C5E governed delivery"
                ),
                body=(
                    "Synthetic C5E body"
                ),
                received_at=(
                    timezone.now()
                ),
                is_read=True,
                is_draft=is_draft,
                status=status,
                retry_count=(
                    retry_count
                ),
                error_reason=(
                    error_reason
                ),
            )
        )


    # ========================================================
    # 1. Shared delivery task must never send an inbound row.
    # ========================================================

    @patch(
        "inbox.tasks._deliver_reply_message"
    )
    def test_async_delivery_blocks_inbound_message(
        self,
        provider,
    ):
        message = (
            self.message(
                direction="inbound",
                status="failed",
            )
        )


        result = (
            send_email_task.run(
                self.account.id,
                message.recipients,
                message.subject,
                message.body,
                message.id,
                allow_retry=False,
            )
        )


        provider.assert_not_called()


        self.assertEqual(
            result[
                "status"
            ],
            "blocked",
        )

        self.assertEqual(
            result[
                "reason"
            ],
            "invalid_delivery_message",
        )


    # ========================================================
    # 2. Shared delivery task must never deliver a draft row.
    # ========================================================

    @patch(
        "inbox.tasks._deliver_reply_message"
    )
    def test_async_delivery_blocks_draft_message(
        self,
        provider,
    ):
        message = (
            self.message(
                is_draft=True,
                status="failed",
            )
        )


        result = (
            send_email_task.run(
                self.account.id,
                message.recipients,
                message.subject,
                message.body,
                message.id,
                allow_retry=False,
            )
        )


        provider.assert_not_called()


        self.assertEqual(
            result[
                "reason"
            ],
            "invalid_delivery_message",
        )


    # ========================================================
    # 3. A disabled mailbox must block queued/retry provider I/O.
    # ========================================================

    @patch(
        "inbox.tasks._deliver_reply_message"
    )
    def test_async_delivery_blocks_inactive_mailbox(
        self,
        provider,
    ):
        self.account.is_active = (
            False
        )

        self.account.save(
            update_fields=[
                "is_active",
            ]
        )


        message = (
            self.message(
                status="failed",
            )
        )


        result = (
            send_email_task.run(
                self.account.id,
                message.recipients,
                message.subject,
                message.body,
                message.id,
                allow_retry=False,
            )
        )


        provider.assert_not_called()


        self.assertEqual(
            result[
                "reason"
            ],
            "inactive_mailbox",
        )


        message.refresh_from_db()


        self.assertEqual(
            message.status,
            "failed",
        )


    # ========================================================
    # 4. Durable local uncertain state blocks provider replay
    # even if the Redis safety store is unavailable.
    # ========================================================

    @patch(
        "inbox.tasks._deliver_reply_message"
    )
    @patch(
        "inbox.tasks.get_outbound_intent_for_message"
    )
    def test_durable_uncertain_marker_blocks_store_outage_replay(
        self,
        get_intent,
        provider,
    ):
        message = (
            self.message(
                status="failed",
                retry_count=1,
                error_reason=(
                    DELIVERY_UNCERTAIN_ERROR_PREFIX
                    + ": synthetic transport timeout"
                ),
            )
        )


        get_intent.side_effect = (
            OutboundIdempotencyUnavailable(
                "synthetic store outage"
            )
        )


        result = (
            send_email_task.run(
                self.account.id,
                message.recipients,
                message.subject,
                message.body,
                message.id,
                allow_retry=False,
            )
        )


        provider.assert_not_called()

        get_intent.assert_called_once_with(
            user_id=self.user.id,
            message_id=message.id,
        )


        self.assertEqual(
            result[
                "status"
            ],
            "delivery_uncertain",
        )


    # ========================================================
    # 5. A repeated failed delivery must fail closed if its
    # idempotency state cannot be read.
    # ========================================================

    @patch(
        "inbox.tasks._deliver_reply_message"
    )
    @patch(
        "inbox.tasks.get_outbound_intent_for_message"
    )
    def test_repeat_delivery_blocks_when_safety_state_unavailable(
        self,
        get_intent,
        provider,
    ):
        message = (
            self.message(
                status="failed",
                retry_count=1,
            )
        )


        get_intent.side_effect = (
            OutboundIdempotencyUnavailable(
                "synthetic store outage"
            )
        )


        result = (
            send_email_task.run(
                self.account.id,
                message.recipients,
                message.subject,
                message.body,
                message.id,
                allow_retry=False,
            )
        )


        provider.assert_not_called()


        self.assertEqual(
            result[
                "reason"
            ],
            "idempotency_unavailable",
        )


        message.refresh_from_db()


        self.assertEqual(
            message.status,
            "failed",
        )


    # ========================================================
    # 6. Periodic retry query is explicitly outbound/non-draft.
    # ========================================================

    @patch(
        "inbox.tasks.create_notification"
    )
    @patch(
        "inbox.tasks.send_email_task.run"
    )
    def test_periodic_retry_ignores_inbound_and_draft_rows(
        self,
        governed_run,
        notification,
    ):
        self.message(
            direction="inbound",
            status="failed",
        )

        self.message(
            direction="outbound",
            is_draft=True,
            status="failed",
        )


        result = (
            retry_failed_messages.run()
        )


        governed_run.assert_not_called()
        notification.assert_not_called()


        self.assertEqual(
            result[
                "scanned"
            ],
            0,
        )


    # ========================================================
    # 7. Missing mailbox must fail closed; another active
    # mailbox must never be guessed.
    # ========================================================

    @patch(
        "inbox.tasks.create_notification"
    )
    @patch(
        "inbox.tasks.send_email_task.run"
    )
    def test_periodic_retry_never_guesses_missing_mailbox(
        self,
        governed_run,
        notification,
    ):
        EmailAccount.objects.create(
            user=self.user,
            organization=(
                self.organization
            ),
            account_type="outlook",
            email_address=(
                "other-c5e@outlook.test"
            ),
            credential_status="active",
            is_active=True,
        )


        message = (
            self.message(
                account=None,
                status="failed",
                retry_count=1,
            )
        )


        result = (
            retry_failed_messages.run()
        )


        governed_run.assert_not_called()


        message.refresh_from_db()


        self.assertEqual(
            message.status,
            "failed",
        )

        self.assertIn(
            "not bound to a mailbox",
            message.error_reason,
        )


        self.assertEqual(
            result[
                "blocked"
            ],
            1,
        )


    # ========================================================
    # 8. Completed provider intent repairs local state without
    # another provider call.
    # ========================================================

    @patch(
        "inbox.tasks.create_notification"
    )
    @patch(
        "inbox.tasks._deliver_reply_message"
    )
    @patch(
        "inbox.tasks.get_outbound_intent_for_message"
    )
    def test_periodic_retry_repairs_completed_intent_without_resend(
        self,
        get_intent,
        provider,
        notification,
    ):
        message = (
            self.message(
                status="failed",
                retry_count=1,
            )
        )


        get_intent.return_value = {
            "state":
                "completed",

            "provider_message_id":
                "c5e-provider-completed",
        }


        result = (
            retry_failed_messages.run()
        )


        provider.assert_not_called()


        message.refresh_from_db()


        self.assertEqual(
            message.status,
            "sent",
        )

        self.assertEqual(
            message.external_message_id,
            "c5e-provider-completed",
        )


        self.assertEqual(
            result[
                "retried"
            ],
            1,
        )


    # ========================================================
    # 9. A completed provider intent remains authoritative even
    # if the mailbox was disabled before local recovery.
    #
    # Recovery is provider-free and must repair the message
    # rather than incorrectly recording a delivered email as
    # blocked/failed.
    # ========================================================

    @patch(
        "inbox.tasks.create_notification"
    )
    @patch(
        "inbox.tasks._deliver_reply_message"
    )
    @patch(
        "inbox.tasks.get_outbound_intent_for_message"
    )
    def test_completed_intent_repairs_after_mailbox_deactivation(
        self,
        get_intent,
        provider,
        notification,
    ):
        message = (
            self.message(
                status="failed",
                retry_count=1,
            )
        )


        self.account.is_active = (
            False
        )

        self.account.save(
            update_fields=[
                "is_active",
            ]
        )


        get_intent.return_value = {
            "state":
                "completed",

            "provider_message_id":
                "c5e-inactive-provider-completed",
        }


        result = (
            retry_failed_messages.run()
        )


        provider.assert_not_called()


        message.refresh_from_db()


        self.assertEqual(
            message.status,
            "sent",
        )

        self.assertEqual(
            message.external_message_id,
            "c5e-inactive-provider-completed",
        )


        self.assertEqual(
            result[
                "retried"
            ],
            1,
        )


    # ========================================================
    # 10. delivery_uncertain intent never reaches provider.
    # ========================================================

    @patch(
        "inbox.tasks.create_notification"
    )
    @patch(
        "inbox.tasks._deliver_reply_message"
    )
    @patch(
        "inbox.tasks.get_outbound_intent_for_message"
    )
    def test_periodic_retry_never_resends_uncertain_intent(
        self,
        get_intent,
        provider,
        notification,
    ):
        message = (
            self.message(
                status="failed",
                retry_count=1,
            )
        )


        get_intent.return_value = {
            "state":
                "delivery_uncertain",
        }


        result = (
            retry_failed_messages.run()
        )


        provider.assert_not_called()


        message.refresh_from_db()


        self.assertEqual(
            message.status,
            "failed",
        )

        self.assertEqual(
            result[
                "blocked"
            ],
            1,
        )


    # ========================================================
    # 11. A valid governed legacy retry uses the message's
    # exact bound mailbox and can complete normally.
    # ========================================================

    @patch(
        "inbox.tasks.create_notification"
    )
    @patch(
        "inbox.tasks._deliver_reply_message"
    )
    @patch(
        "inbox.tasks.get_outbound_intent_for_message"
    )
    def test_periodic_retry_uses_exact_bound_mailbox(
        self,
        get_intent,
        provider,
        notification,
    ):
        other = (
            EmailAccount.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                account_type="outlook",
                email_address=(
                    "other-bound-c5e@outlook.test"
                ),
                credential_status="active",
                is_active=True,
            )
        )


        message = (
            self.message(
                status="failed",
                retry_count=1,
            )
        )


        get_intent.return_value = (
            None
        )

        provider.return_value = {
            "id":
                "c5e-retry-sent",
        }


        result = (
            retry_failed_messages.run()
        )


        provider.assert_called_once()


        self.assertEqual(
            provider
            .call_args
            .kwargs[
                "email_account"
            ]
            .id,
            self.account.id,
        )

        self.assertNotEqual(
            provider
            .call_args
            .kwargs[
                "email_account"
            ]
            .id,
            other.id,
        )


        message.refresh_from_db()


        self.assertEqual(
            message.status,
            "sent",
        )

        self.assertEqual(
            message.external_message_id,
            "c5e-retry-sent",
        )

        self.assertEqual(
            result[
                "retried"
            ],
            1,
        )


    # ========================================================
    # 12. Periodic governed execution must never create a
    # nested Celery retry loop on provider failure.
    # ========================================================

    @patch(
        "inbox.tasks.create_notification"
    )
    @patch.object(
        send_email_task,
        "retry",
    )
    @patch(
        "inbox.tasks._deliver_reply_message"
    )
    @patch(
        "inbox.tasks.get_outbound_intent_for_message"
    )
    def test_periodic_provider_failure_stays_failed_without_nested_retry(
        self,
        get_intent,
        provider,
        task_retry,
        notification,
    ):
        message = (
            self.message(
                status="failed",
                retry_count=1,
            )
        )


        get_intent.return_value = (
            None
        )

        provider.side_effect = (
            ValueError(
                "synthetic provider failure"
            )
        )


        result = (
            retry_failed_messages.run()
        )


        task_retry.assert_not_called()


        message.refresh_from_db()


        self.assertEqual(
            message.status,
            "failed",
        )

        self.assertEqual(
            message.retry_count,
            2,
        )

        self.assertEqual(
            result[
                "failed"
            ],
            1,
        )
