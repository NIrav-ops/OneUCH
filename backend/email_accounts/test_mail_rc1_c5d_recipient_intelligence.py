from datetime import (
    datetime,
    timezone as dt_timezone,
)

from unittest.mock import (
    Mock,
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

from rest_framework.test import (
    APIClient,
)

from actions.models import (
    AIActionCandidate,
    ExpectedResponseItem,
    FollowUpItem,
)

from actions.tasks import (
    analyze_new_messages,
)

from actions.followup_tasks import (
    analyze_new_followups,
)

from actions.expected_response_tasks import (
    analyze_new_expected_responses,
)

from approvals.models import (
    AIApprovalCandidate,
)

from approvals.tasks import (
    analyze_new_approvals,
)

from context.models import (
    BusinessObject,
    BusinessObjectType,
)

from email_accounts.models import (
    EmailAccount,
)

from inbox.models import (
    Conversation,
    InboxMessage,
    Organization,
    OrganizationUser,
    RecipientContact,
    RecipientDirectoryState,
)

from inbox.services.recipient_directory import (
    refresh_recipient_directory,
)

from inbox.tasks import (
    sync_email_account,
)

from knowledge.models import (
    BusinessIdentity,
    KnowledgeEvidence,
)

from knowledge.services.message_processor import (
    MessageProcessor,
)


User = get_user_model()


class MailRC1C5DRecipientIntelligenceTests(
    TestCase
):

    MAIL_PASSWORD = (
        "C5D-Synthetic-Mail-Credential-84271"
    )


    def setUp(
        self,
    ):
        self.user = (
            User.objects.create_user(
                email=(
                    "c5d-owner@oneuch.test"
                ),
                password=(
                    "C5D-Password-84271"
                ),
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
                    self.MAIL_PASSWORD
                ),
                credential_status="active",
                is_active=True,
            )
        )


        self.client = (
            APIClient()
        )

        self.client.force_authenticate(
            user=self.user
        )


    def conversation(
        self,
    ):
        return (
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


    def message(
        self,
        *,
        sender="customer@example.net",
        recipients=None,
        subject="C5D",
        body="Body",
        direction="inbound",
        conversation=None,
        account=None,
        user=None,
        organization=None,
        external_id=None,
        sender_meta=None,
        recipient_meta=None,
        action_analyzed=False,
        approval_analyzed=False,
        followup_analyzed=False,
        expected_response_analyzed=False,
    ):
        account = (
            account
            or
            self.account
        )

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


        if recipients is None:

            recipients = (
                account.email_address
                if direction
                ==
                "inbound"
                else
                "customer@example.net"
            )


        if sender_meta is None:

            sender_meta = {
                "name":
                    (
                        "Customer"
                        if direction
                        ==
                        "inbound"
                        else ""
                    ),

                "email":
                    sender,
            }


        if recipient_meta is None:

            recipient_meta = {
                "to": [
                    {
                        "name":
                            "",

                        "email":
                            recipients,
                    }
                ],

                "cc":
                    [],

                "bcc":
                    [],

                "reply_to":
                    [],
            }


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
                    else
                    "inbox"
                ),
                conversation=(
                    conversation
                ),
                external_message_id=(
                    external_id
                    or
                    (
                        "c5d-msg-"
                        + uuid4().hex
                    )
                ),
                sender=sender,
                recipients=(
                    recipients
                ),
                sender_meta=(
                    sender_meta
                ),
                recipient_meta=(
                    recipient_meta
                ),
                subject=subject,
                body=body,
                received_at=(
                    datetime(
                        2026,
                        9,
                        7,
                        7,
                        0,
                        tzinfo=(
                            dt_timezone.utc
                        ),
                    )
                ),
                is_read=True,
                is_draft=False,
                status=(
                    "sent"
                    if direction
                    ==
                    "outbound"
                    else
                    "queued"
                ),
                action_analyzed=(
                    action_analyzed
                ),
                approval_analyzed=(
                    approval_analyzed
                ),
                followup_analyzed=(
                    followup_analyzed
                ),
                expected_response_analyzed=(
                    expected_response_analyzed
                ),
            )
        )


    # ========================================================
    # 1. IMAP structured identities participate in recipient
    # intelligence with role counters and self-address removal.
    # ========================================================

    def test_imap_recipient_directory_indexes_structured_identities(
        self,
    ):
        self.message(
            sender=(
                "alice@example.net"
            ),
            sender_meta={
                "name":
                    "Alice Customer",

                "email":
                    "alice@example.net",
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
                            "Alice Customer",

                        "email":
                            "alice@example.net",
                    }
                ],
            },
        )


        self.message(
            direction="outbound",
            sender=(
                self.account
                .email_address
            ),
            recipients=(
                "alice@example.net, "
                "finance@example.net, "
                "audit@example.net"
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
                            "Alice Customer",

                        "email":
                            "alice@example.net",
                    }
                ],

                "cc": [
                    {
                        "name":
                            "Finance",

                        "email":
                            "finance@example.net",
                    }
                ],

                "bcc": [
                    {
                        "name":
                            "Audit",

                        "email":
                            "audit@example.net",
                    }
                ],

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
            2,
        )

        self.assertEqual(
            state.indexed_message_count,
            2,
        )


        alice = (
            RecipientContact.objects
            .get(
                user=self.user,
                organization=(
                    self.organization
                ),
                normalized_email=(
                    "alice@example.net"
                ),
            )
        )


        self.assertEqual(
            alice.message_count,
            2,
        )

        self.assertEqual(
            alice.received_count,
            1,
        )

        self.assertEqual(
            alice.sent_count,
            1,
        )

        self.assertEqual(
            alice.reply_to_count,
            1,
        )


        self.assertEqual(
            RecipientContact.objects
            .get(
                user=self.user,
                normalized_email=(
                    "finance@example.net"
                ),
            )
            .cc_count,
            1,
        )


        self.assertEqual(
            RecipientContact.objects
            .get(
                user=self.user,
                normalized_email=(
                    "audit@example.net"
                ),
            )
            .bcc_count,
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


    # ========================================================
    # 2. Previously-excluded IMAP rows below an existing
    # Gmail/Outlook watermark are rebuilt into the directory.
    # ========================================================

    def test_recipient_directory_backfills_imap_below_old_watermark(
        self,
    ):
        old_imap = (
            self.message(
                sender=(
                    "historical-imap@example.net"
                ),
            )
        )


        gmail_account = (
            EmailAccount.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                account_type="gmail",
                email_address=(
                    "owner@gmail.com"
                ),
                credential_status="active",
                is_active=True,
            )
        )


        gmail_message = (
            self.message(
                sender=(
                    "gmail-contact@example.net"
                ),
                account=(
                    gmail_account
                ),
                external_id=(
                    "c5d-gmail-watermark"
                ),
            )
        )


        self.assertLess(
            old_imap.id,
            gmail_message.id,
        )


        with patch(
            (
                "inbox.services."
                "recipient_directory."
                "SUPPORTED_PLATFORMS"
            ),
            (
                "gmail",
                "outlook",
            ),
        ):

            first_state, first_processed = (
                refresh_recipient_directory(
                    user=self.user
                )
            )


        self.assertEqual(
            first_processed,
            1,
        )

        self.assertEqual(
            first_state.indexed_message_count,
            1,
        )

        self.assertEqual(
            first_state.last_indexed_message_id,
            gmail_message.id,
        )


        second_state, second_processed = (
            refresh_recipient_directory(
                user=self.user
            )
        )


        self.assertEqual(
            second_processed,
            2,
        )

        self.assertEqual(
            second_state.indexed_message_count,
            2,
        )


        self.assertTrue(
            RecipientContact.objects
            .filter(
                user=self.user,
                normalized_email=(
                    "historical-imap@example.net"
                ),
            )
            .exists()
        )

        self.assertTrue(
            RecipientContact.objects
            .filter(
                user=self.user,
                normalized_email=(
                    "gmail-contact@example.net"
                ),
            )
            .exists()
        )


    # ========================================================
    # 3. Autocomplete exposes IMAP-derived contacts while
    # retaining user/workspace isolation.
    # ========================================================

    def test_imap_recipient_suggestions_are_tenant_scoped(
        self,
    ):
        self.message(
            sender=(
                "imap-suggestion@example.net"
            ),
            sender_meta={
                "name":
                    "IMAP Suggestion",

                "email":
                    "imap-suggestion@example.net",
            },
        )


        other_user = (
            User.objects.create_user(
                email=(
                    "c5d-other@oneuch.test"
                ),
                password=(
                    "C5D-Other-84271"
                ),
            )
        )


        other_org = (
            Organization.objects.create(
                name="Other C5D",
                slug=(
                    "other-c5d-"
                    + uuid4().hex
                ),
            )
        )


        OrganizationUser.objects.create(
            user=other_user,
            organization=(
                other_org
            ),
            role="owner",
        )


        other_account = (
            EmailAccount.objects.create(
                user=other_user,
                organization=(
                    other_org
                ),
                account_type="imap",
                email_address=(
                    "other@example.com"
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
                    self.MAIL_PASSWORD
                ),
                credential_status="active",
                is_active=True,
            )
        )


        self.message(
            sender=(
                "private-other@example.net"
            ),
            account=(
                other_account
            ),
            user=(
                other_user
            ),
            organization=(
                other_org
            ),
        )


        response = (
            self.client.get(
                (
                    "/api/inbox/"
                    "recipient-suggestions/"
                    "?q=imap"
                )
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        emails = [
            item[
                "email"
            ]

            for item in (
                response.data[
                    "results"
                ]
            )
        ]


        self.assertIn(
            "imap-suggestion@example.net",
            emails,
        )

        self.assertNotIn(
            "private-other@example.net",
            emails,
        )


    # ========================================================
    # 4. IMAP MessageProcessor evidence is EMAIL, not GENERAL.
    # ========================================================

    def test_imap_message_processor_creates_email_evidence(
        self,
    ):
        object_type = (
            BusinessObjectType.objects.create(
                name=(
                    "C5D Company "
                    + uuid4().hex
                )
            )
        )


        business_object = (
            BusinessObject.objects.create(
                organization=(
                    self.organization
                ),
                object_type=(
                    object_type
                ),
                name=(
                    "C5D Customer"
                ),
                status="active",
            )
        )


        BusinessIdentity.objects.create(
            business_object=(
                business_object
            ),
            identity_type="EMAIL",
            value=(
                "knowledge@example.net"
            ),
            normalized_value=(
                "knowledge@example.net"
            ),
            source="manual",
        )


        message = (
            self.message(
                sender=(
                    "knowledge@example.net"
                ),
                conversation=(
                    self.conversation()
                ),
                subject=(
                    "C5D knowledge"
                ),
                body=(
                    "Knowledge evidence"
                ),
            )
        )


        result = (
            MessageProcessor()
            .process_message(
                organization=(
                    self.organization
                ),
                message=message,
                sender=(
                    message.sender
                ),
                subject=(
                    message.subject
                ),
                body=(
                    message.body
                ),
                source_channel="imap",
            )
        )


        self.assertTrue(
            result[
                "matched"
            ]
        )


        evidence = (
            KnowledgeEvidence.objects
            .get(
                message=message
            )
        )


        self.assertEqual(
            evidence.evidence_type,
            "EMAIL",
        )


    # ========================================================
    # 5. One successful IMAP sync queues all four analyzers
    # only for pending messages from that mailbox.
    # ========================================================

    @patch(
        "inbox.tasks.release_sync_lock"
    )
    @patch(
        "inbox.tasks.analyze_new_expected_responses.delay"
    )
    @patch(
        "inbox.tasks.analyze_new_followups.delay"
    )
    @patch(
        "inbox.tasks.analyze_new_approvals.delay"
    )
    @patch(
        "inbox.tasks.analyze_new_messages.delay"
    )
    @patch(
        "inbox.tasks.fetch_imap_emails"
    )
    @patch(
        "inbox.tasks.acquire_sync_lock"
    )
    def test_imap_sync_queues_four_scoped_intelligence_analyzers(
        self,
        acquire_lock,
        fetch_imap,
        action_delay,
        approval_delay,
        followup_delay,
        expected_delay,
        release_lock,
    ):
        own_message = (
            self.message(
                body=(
                    "Please send the revised quotation "
                    "by Friday."
                ),
            )
        )


        other_user = (
            User.objects.create_user(
                email=(
                    "handoff-other@oneuch.test"
                ),
                password=(
                    "C5D-Other-Password"
                ),
            )
        )


        other_org = (
            Organization.objects.create(
                name="Handoff Other",
                slug=(
                    "handoff-other-"
                    + uuid4().hex
                ),
            )
        )


        OrganizationUser.objects.create(
            user=other_user,
            organization=(
                other_org
            ),
            role="owner",
        )


        other_account = (
            EmailAccount.objects.create(
                user=other_user,
                organization=(
                    other_org
                ),
                account_type="imap",
                email_address=(
                    "other-handoff@example.com"
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
                    self.MAIL_PASSWORD
                ),
                credential_status="active",
                is_active=True,
            )
        )


        foreign_message = (
            self.message(
                account=(
                    other_account
                ),
                user=(
                    other_user
                ),
                organization=(
                    other_org
                ),
            )
        )


        lock = (
            Mock()
        )

        acquire_lock.return_value = (
            lock
        )


        result = (
            sync_email_account.run(
                self.account.id
            )
        )


        fetch_imap.assert_called_once()


        expected_call = {
            "message_ids": [
                own_message.id
            ]
        }


        self.assertEqual(
            action_delay.call_args.kwargs,
            expected_call,
        )

        self.assertEqual(
            approval_delay.call_args.kwargs,
            expected_call,
        )

        self.assertEqual(
            followup_delay.call_args.kwargs,
            expected_call,
        )

        self.assertEqual(
            expected_delay.call_args.kwargs,
            expected_call,
        )


        self.assertNotIn(
            foreign_message.id,
            result.get(
                "message_ids",
                [],
            ),
        )


        self.assertEqual(
            result[
                "intelligence_messages"
            ],
            1,
        )

        self.assertEqual(
            result[
                "intelligence_batches"
            ],
            1,
        )


        release_lock.assert_called_once_with(
            lock
        )


    # ========================================================
    # 6. No pending mailbox intelligence means no global
    # analyzer task is queued.
    # ========================================================

    @patch(
        "inbox.tasks.release_sync_lock"
    )
    @patch(
        "inbox.tasks.analyze_new_expected_responses.delay"
    )
    @patch(
        "inbox.tasks.analyze_new_followups.delay"
    )
    @patch(
        "inbox.tasks.analyze_new_approvals.delay"
    )
    @patch(
        "inbox.tasks.analyze_new_messages.delay"
    )
    @patch(
        "inbox.tasks.fetch_imap_emails"
    )
    @patch(
        "inbox.tasks.acquire_sync_lock"
    )
    def test_sync_with_no_pending_messages_queues_no_global_analysis(
        self,
        acquire_lock,
        fetch_imap,
        action_delay,
        approval_delay,
        followup_delay,
        expected_delay,
        release_lock,
    ):
        self.message(
            action_analyzed=True,
            approval_analyzed=True,
            followup_analyzed=True,
            expected_response_analyzed=True,
        )


        lock = (
            Mock()
        )

        acquire_lock.return_value = (
            lock
        )


        result = (
            sync_email_account.run(
                self.account.id
            )
        )


        action_delay.assert_not_called()
        approval_delay.assert_not_called()
        followup_delay.assert_not_called()
        expected_delay.assert_not_called()


        self.assertEqual(
            result[
                "intelligence_messages"
            ],
            0,
        )

        self.assertEqual(
            result[
                "intelligence_batches"
            ],
            0,
        )


        release_lock.assert_called_once_with(
            lock
        )


    # ========================================================
    # 7. IMAP messages enter deterministic Action analysis
    # without invoking semantic AI.
    # ========================================================

    @patch(
        "actions.tasks."
        "extract_actions_with_ai_result"
    )
    def test_imap_deterministic_action_parity(
        self,
        ai_extract,
    ):
        message = (
            self.message(
                subject=(
                    "Quotation required"
                ),
                body=(
                    "Please send the revised quotation "
                    "by Friday."
                ),
            )
        )


        processed = (
            analyze_new_messages.run(
                message_ids=[
                    message.id
                ]
            )
        )


        self.assertEqual(
            processed,
            1,
        )

        ai_extract.assert_not_called()


        candidate = (
            AIActionCandidate.objects
            .get(
                message=message
            )
        )


        self.assertEqual(
            candidate.extraction_method,
            "deterministic",
        )


        message.refresh_from_db()


        self.assertTrue(
            message.action_analyzed
        )


    # ========================================================
    # 8. IMAP messages enter deterministic Approval analysis
    # without invoking semantic AI.
    # ========================================================

    @patch(
        "approvals.tasks."
        "extract_approvals_with_ai_result"
    )
    def test_imap_deterministic_approval_parity(
        self,
        ai_extract,
    ):
        message = (
            self.message(
                subject=(
                    "Proposal approval"
                ),
                body=(
                    "Please approve the attached "
                    "commercial proposal."
                ),
            )
        )


        processed = (
            analyze_new_approvals.run(
                message_ids=[
                    message.id
                ]
            )
        )


        self.assertEqual(
            processed,
            1,
        )

        ai_extract.assert_not_called()


        candidate = (
            AIApprovalCandidate.objects
            .get(
                message=message
            )
        )


        self.assertEqual(
            candidate.extraction_method,
            "deterministic",
        )


        message.refresh_from_db()


        self.assertTrue(
            message.approval_analyzed
        )


    # ========================================================
    # 9. IMAP messages enter deterministic Follow-up analysis.
    # ========================================================

    def test_imap_followup_parity(
        self,
    ):
        conversation = (
            self.conversation()
        )


        message = (
            self.message(
                conversation=(
                    conversation
                ),
                body=(
                    "Please follow up with the vendor "
                    "tomorrow."
                ),
            )
        )


        processed = (
            analyze_new_followups.run(
                message_ids=[
                    message.id
                ]
            )
        )


        self.assertEqual(
            processed,
            1,
        )


        self.assertTrue(
            FollowUpItem.objects
            .filter(
                last_message=message,
                status="pending",
            )
            .exists()
        )


        message.refresh_from_db()


        self.assertTrue(
            message.followup_analyzed
        )


    # ========================================================
    # 10. IMAP messages enter deterministic Expected Response /
    # commitment analysis.
    # ========================================================

    def test_imap_expected_response_commitment_parity(
        self,
    ):
        conversation = (
            self.conversation()
        )


        message = (
            self.message(
                conversation=(
                    conversation
                ),
                body=(
                    "Vendor will confirm tomorrow."
                ),
            )
        )


        processed = (
            analyze_new_expected_responses.run(
                message_ids=[
                    message.id
                ]
            )
        )


        self.assertEqual(
            processed,
            1,
        )


        self.assertTrue(
            ExpectedResponseItem.objects
            .filter(
                source_message=message,
                status="waiting",
            )
            .exists()
        )


        message.refresh_from_db()


        self.assertTrue(
            message
            .expected_response_analyzed
        )
