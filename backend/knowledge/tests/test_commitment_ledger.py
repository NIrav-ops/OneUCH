from datetime import (
    datetime,
    timezone as dt_timezone,
)

from django.contrib.auth import (
    get_user_model,
)
from django.test import TestCase

from actions.models import (
    ActionItem,
    ExpectedResponseItem,
)
from inbox.models import (
    Conversation,
    InboxMessage,
    Organization,
)
from knowledge.services.commitment_ledger import (
    CommitmentLedgerService,
)
from knowledge.services.intelligence_evidence_persistence import (
    persist_intelligence_evidence,
)


User = get_user_model()


class CommitmentLedgerServiceTests(
    TestCase
):

    def setUp(self):
        self.user = User.objects.create_user(
            email="owner@oneuch.test",
            password="pass123",
        )

        self.organization = (
            Organization.objects.create(
                name="Commitment Ledger Org",
                slug="commitment-ledger-org",
            )
        )

        self.other_organization = (
            Organization.objects.create(
                name="Other Org",
                slug="commitment-other-org",
            )
        )

        self.conversation = (
            Conversation.objects.create(
                user=self.user,
                organization=self.organization,
                conversation_key=(
                    "commitment-ledger-thread"
                ),
                subject="Pricing",
            )
        )

        self.counter = 0

    def message(
        self,
        *,
        body,
        subject="Commitment",
        direction="inbound",
        sender=None,
        recipients=None,
    ):
        self.counter += 1

        if sender is None:
            sender = (
                "customer@example.com"
                if direction == "inbound"
                else self.user.email
            )

        if recipients is None:
            recipients = (
                self.user.email
                if direction == "inbound"
                else "vendor@example.com"
            )

        return InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            platform="gmail",
            direction=direction,
            external_message_id=(
                "commitment-ledger-"
                f"{self.counter}"
            ),
            sender=sender,
            recipients=recipients,
            subject=subject,
            body=body,
            received_at=datetime(
                2026,
                8,
                28,
                6,
                self.counter,
                tzinfo=dt_timezone.utc,
            ),
        )

    def test_action_projects_we_owe_them(
        self,
    ):
        msg = self.message(
            body=(
                "Please send revised pricing "
                "tomorrow."
            )
        )

        action = ActionItem.objects.create(
            user=self.user,
            organization=self.organization,
            message=msg,
            title="Send revised pricing",
            owner=self.user,
            due_date=datetime(
                2026,
                8,
                29,
                6,
                0,
                tzinfo=dt_timezone.utc,
            ),
            source_type="email",
            confidence_score=80,
        )

        persist_intelligence_evidence(
            action,
            evidence_text=(
                "Please send revised pricing "
                "tomorrow."
            ),
            extraction_method=(
                "deterministic"
            ),
            processing_mode=(
                "deterministic"
            ),
            confidence=80,
        )

        entries = (
            CommitmentLedgerService.build(
                organization=(
                    self.organization
                )
            )
        )

        self.assertEqual(
            len(entries),
            1,
        )

        entry = entries[0]

        self.assertEqual(
            entry.commitment_id,
            f"action:{action.id}",
        )

        self.assertEqual(
            entry.direction,
            "WE_OWE_THEM",
        )

        self.assertEqual(
            entry.counterparty,
            "customer@example.com",
        )

        self.assertEqual(
            entry.owner_id,
            self.user.id,
        )

        self.assertEqual(
            entry.status,
            "pending",
        )

        self.assertEqual(
            entry.evidence[
                "evidence_quality"
            ],
            "exact",
        )

    def test_completed_action_projects_fulfilled(
        self,
    ):
        msg = self.message(
            body=(
                "Please send quotation."
            )
        )

        completed_at = datetime(
            2026,
            8,
            28,
            8,
            0,
            tzinfo=dt_timezone.utc,
        )

        ActionItem.objects.create(
            user=self.user,
            organization=self.organization,
            message=msg,
            title="Send quotation",
            source_type="email",
            status="completed",
            completed_at=completed_at,
            confidence_score=80,
        )

        entry = (
            CommitmentLedgerService.build(
                organization=(
                    self.organization
                )
            )[0]
        )

        self.assertEqual(
            entry.status,
            "fulfilled",
        )

        self.assertEqual(
            entry.resolved_at,
            completed_at,
        )

    def test_ai_action_is_included(
        self,
    ):
        msg = self.message(
            body=(
                "Please provide deployment "
                "plan tomorrow."
            )
        )

        action = ActionItem.objects.create(
            user=self.user,
            organization=self.organization,
            message=msg,
            title="Provide deployment plan",
            source_type="ai",
            confidence_score=97,
        )

        persist_intelligence_evidence(
            action,
            evidence_text=(
                "Please provide deployment "
                "plan tomorrow."
            ),
            extraction_method="ai",
            processing_mode="cloud",
            provider="openai",
            model="test-model",
            confidence=97,
        )

        entry = (
            CommitmentLedgerService.build(
                organization=(
                    self.organization
                )
            )[0]
        )

        self.assertEqual(
            entry.direction,
            "WE_OWE_THEM",
        )

        self.assertEqual(
            entry.evidence[
                "processing_mode"
            ],
            "cloud",
        )

    def test_manual_action_is_not_assumed_commitment(
        self,
    ):
        msg = self.message(
            body="Internal reminder."
        )

        ActionItem.objects.create(
            user=self.user,
            organization=self.organization,
            message=msg,
            title="Internal task",
            source_type="manual",
            confidence_score=100,
        )

        entries = (
            CommitmentLedgerService.build(
                organization=(
                    self.organization
                )
            )
        )

        self.assertEqual(
            entries,
            [],
        )

    def test_outbound_action_is_not_assumed_we_owe_them(
        self,
    ):
        msg = self.message(
            direction="outbound",
            body="We sent an update.",
        )

        ActionItem.objects.create(
            user=self.user,
            organization=self.organization,
            message=msg,
            title="Outbound generated action",
            source_type="email",
            confidence_score=80,
        )

        entries = (
            CommitmentLedgerService.build(
                organization=(
                    self.organization
                )
            )
        )

        self.assertEqual(
            entries,
            [],
        )

    def test_expected_response_projects_they_owe_us(
        self,
    ):
        msg = self.message(
            sender="vendor@example.com",
            body=(
                "Vendor will confirm tomorrow."
            ),
        )

        item = (
            ExpectedResponseItem.objects.create(
                user=self.user,
                organization=self.organization,
                conversation=self.conversation,
                source_message=msg,
                evidence_text=(
                    "Vendor will confirm tomorrow."
                ),
                response_due_at=datetime(
                    2026,
                    8,
                    29,
                    0,
                    0,
                    tzinfo=dt_timezone.utc,
                ),
                status="waiting",
            )
        )

        persist_intelligence_evidence(
            item,
            evidence_text=(
                "Vendor will confirm tomorrow."
            ),
            extraction_method=(
                "deterministic"
            ),
            processing_mode=(
                "deterministic"
            ),
            confidence=100,
        )

        entry = (
            CommitmentLedgerService.build(
                organization=(
                    self.organization
                )
            )[0]
        )

        self.assertEqual(
            entry.commitment_id,
            (
                "expected_response:"
                f"{item.id}"
            ),
        )

        self.assertEqual(
            entry.direction,
            "THEY_OWE_US",
        )

        self.assertEqual(
            entry.counterparty,
            "vendor@example.com",
        )

        self.assertEqual(
            entry.owner_id,
            self.user.id,
        )

        self.assertEqual(
            entry.status,
            "pending",
        )

        self.assertEqual(
            entry.evidence[
                "evidence_quality"
            ],
            "exact",
        )

    def test_outbound_expected_response_uses_recipient(
        self,
    ):
        msg = self.message(
            direction="outbound",
            recipients=(
                "Vendor Team "
                "<vendor@example.com>, "
                "copy@example.com"
            ),
            body=(
                "Please let me know once approved."
            ),
        )

        ExpectedResponseItem.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            source_message=msg,
            evidence_text=(
                "Please let me know once approved."
            ),
            status="waiting",
        )

        entry = (
            CommitmentLedgerService.build(
                organization=(
                    self.organization
                )
            )[0]
        )

        self.assertEqual(
            entry.counterparty,
            "vendor@example.com",
        )

    def test_explicit_expected_from_wins(
        self,
    ):
        msg = self.message(
            sender="sender@example.com",
            body=(
                "Vendor will confirm tomorrow."
            ),
        )

        ExpectedResponseItem.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            source_message=msg,
            expected_from=(
                "accounts@vendor.com"
            ),
            evidence_text=(
                "Vendor will confirm tomorrow."
            ),
            status="waiting",
        )

        entry = (
            CommitmentLedgerService.build(
                organization=(
                    self.organization
                )
            )[0]
        )

        self.assertEqual(
            entry.counterparty,
            "accounts@vendor.com",
        )

    def test_received_expected_response_is_fulfilled(
        self,
    ):
        msg = self.message(
            body=(
                "Vendor will confirm tomorrow."
            )
        )

        resolved_at = datetime(
            2026,
            8,
            29,
            7,
            0,
            tzinfo=dt_timezone.utc,
        )

        ExpectedResponseItem.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            source_message=msg,
            evidence_text=(
                "Vendor will confirm tomorrow."
            ),
            status="received",
            resolved_at=resolved_at,
        )

        entry = (
            CommitmentLedgerService.build(
                organization=(
                    self.organization
                )
            )[0]
        )

        self.assertEqual(
            entry.status,
            "fulfilled",
        )

        self.assertEqual(
            entry.resolved_at,
            resolved_at,
        )

    def test_organization_isolation(
        self,
    ):
        msg = self.message(
            body="Please send quotation."
        )

        ActionItem.objects.create(
            user=self.user,
            organization=self.organization,
            message=msg,
            title="Send quotation",
            source_type="email",
            confidence_score=80,
        )

        entries = (
            CommitmentLedgerService.build(
                organization=(
                    self.other_organization
                )
            )
        )

        self.assertEqual(
            entries,
            [],
        )

    def test_to_dict_preserves_nested_evidence(
        self,
    ):
        msg = self.message(
            body="Please send quotation."
        )

        ActionItem.objects.create(
            user=self.user,
            organization=self.organization,
            message=msg,
            title="Send quotation",
            source_type="email",
            confidence_score=80,
        )

        entry = (
            CommitmentLedgerService.build(
                organization=(
                    self.organization
                )
            )[0]
        )

        payload = entry.to_dict()

        self.assertEqual(
            payload["direction"],
            "WE_OWE_THEM",
        )

        self.assertIn(
            "evidence_quality",
            payload["evidence"],
        )
