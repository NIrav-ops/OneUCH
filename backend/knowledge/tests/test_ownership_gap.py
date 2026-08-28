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
    OrganizationUser,
)

from knowledge.services.intelligence_evidence_persistence import (
    persist_intelligence_evidence,
)
from knowledge.services.ownership_gap import (
    OwnershipGapService,
)


User = get_user_model()


class OwnershipGapServiceTests(
    TestCase
):

    def setUp(self):
        self.user = User.objects.create_user(
            email="owner@ownership.test",
            password="pass123",
        )

        self.organization = (
            Organization.objects.create(
                name="Ownership Org",
                slug="ownership-org",
            )
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=self.organization,
            role="member",
        )

        self.outside_user = (
            User.objects.create_user(
                email="outside@ownership.test",
                password="pass123",
            )
        )

        self.other_organization = (
            Organization.objects.create(
                name="Other Ownership Org",
                slug="other-ownership-org",
            )
        )

        OrganizationUser.objects.create(
            user=self.outside_user,
            organization=(
                self.other_organization
            ),
            role="member",
        )

        self.conversation = (
            Conversation.objects.create(
                user=self.user,
                organization=self.organization,
                conversation_key=(
                    "ownership-gap-thread"
                ),
                subject="Pricing",
            )
        )

        self.counter = 0

    def message(
        self,
        *,
        body,
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
                "ownership-gap-"
                f"{self.counter}"
            ),
            sender=sender,
            recipients=recipients,
            subject="Pricing",
            body=body,
            received_at=datetime(
                2026,
                8,
                28,
                8,
                self.counter,
                tzinfo=dt_timezone.utc,
            ),
        )

    def action(
        self,
        *,
        owner=None,
        status="open",
        source_type="email",
    ):
        msg = self.message(
            body=(
                "Please provide revised "
                "pricing tomorrow."
            )
        )

        return ActionItem.objects.create(
            user=self.user,
            organization=self.organization,
            message=msg,
            title="Provide revised pricing",
            owner=owner,
            status=status,
            source_type=source_type,
            due_date=datetime(
                2026,
                8,
                29,
                8,
                0,
                tzinfo=dt_timezone.utc,
            ),
            confidence_score=80,
        )

    def test_pending_commitment_without_owner_is_gap(
        self,
    ):
        action = self.action(
            owner=None
        )

        findings = (
            OwnershipGapService.build(
                organization=(
                    self.organization
                )
            )
        )

        self.assertEqual(
            len(findings),
            1,
        )

        finding = findings[0]

        self.assertEqual(
            finding.commitment_id,
            f"action:{action.id}",
        )

        self.assertEqual(
            finding.gap_type,
            "unassigned",
        )

        self.assertEqual(
            finding.reason_code,
            "NO_EXPLICIT_OWNER",
        )

        self.assertEqual(
            finding.direction,
            "WE_OWE_THEM",
        )

    def test_valid_organization_owner_resolves_gap(
        self,
    ):
        self.action(
            owner=self.user
        )

        findings = (
            OwnershipGapService.build(
                organization=(
                    self.organization
                )
            )
        )

        self.assertEqual(
            findings,
            [],
        )

    def test_assignment_resolves_existing_gap_dynamically(
        self,
    ):
        action = self.action(
            owner=None
        )

        before = (
            OwnershipGapService.build(
                organization=(
                    self.organization
                )
            )
        )

        self.assertEqual(
            len(before),
            1,
        )

        action.owner = self.user

        action.save(
            update_fields=[
                "owner"
            ]
        )

        after = (
            OwnershipGapService.build(
                organization=(
                    self.organization
                )
            )
        )

        self.assertEqual(
            after,
            [],
        )

    def test_owner_outside_organization_is_gap(
        self,
    ):
        action = self.action(
            owner=self.outside_user
        )

        findings = (
            OwnershipGapService.build(
                organization=(
                    self.organization
                )
            )
        )

        self.assertEqual(
            len(findings),
            1,
        )

        finding = findings[0]

        self.assertEqual(
            finding.source_object_id,
            action.id,
        )

        self.assertEqual(
            finding.gap_type,
            "invalid_owner",
        )

        self.assertEqual(
            finding.reason_code,
            (
                "OWNER_OUTSIDE_ORGANIZATION"
            ),
        )

        self.assertEqual(
            finding.current_owner_id,
            self.outside_user.id,
        )

    def test_completed_commitment_is_not_gap(
        self,
    ):
        self.action(
            owner=None,
            status="completed",
        )

        findings = (
            OwnershipGapService.build(
                organization=(
                    self.organization
                )
            )
        )

        self.assertEqual(
            findings,
            [],
        )

    def test_ignored_commitment_is_not_gap(
        self,
    ):
        self.action(
            owner=None,
            status="ignored",
        )

        findings = (
            OwnershipGapService.build(
                organization=(
                    self.organization
                )
            )
        )

        self.assertEqual(
            findings,
            [],
        )

    def test_they_owe_us_is_not_false_ownership_gap(
        self,
    ):
        msg = self.message(
            sender="vendor@example.com",
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
                "vendor@example.com"
            ),
            evidence_text=(
                "Vendor will confirm tomorrow."
            ),
            status="waiting",
        )

        findings = (
            OwnershipGapService.build(
                organization=(
                    self.organization
                )
            )
        )

        self.assertEqual(
            findings,
            [],
        )

    def test_finding_preserves_exact_commitment_evidence(
        self,
    ):
        action = self.action(
            owner=None
        )

        persist_intelligence_evidence(
            action,
            evidence_text=(
                "Please provide revised "
                "pricing tomorrow."
            ),
            extraction_method=(
                "deterministic"
            ),
            processing_mode=(
                "deterministic"
            ),
            confidence=80,
        )

        finding = (
            OwnershipGapService.build(
                organization=(
                    self.organization
                )
            )[0]
        )

        self.assertEqual(
            finding.evidence[
                "evidence_quality"
            ],
            "exact",
        )

        self.assertEqual(
            finding.evidence[
                "evidence_text"
            ],
            (
                "Please provide revised "
                "pricing tomorrow."
            ),
        )

    def test_organization_isolation(
        self,
    ):
        self.action(
            owner=None
        )

        findings = (
            OwnershipGapService.build(
                organization=(
                    self.other_organization
                )
            )
        )

        self.assertEqual(
            findings,
            [],
        )

    def test_to_dict_is_attention_ready(
        self,
    ):
        self.action(
            owner=None
        )

        finding = (
            OwnershipGapService.build(
                organization=(
                    self.organization
                )
            )[0]
        )

        payload = (
            finding.to_dict()
        )

        self.assertEqual(
            payload[
                "reason_code"
            ],
            "NO_EXPLICIT_OWNER",
        )

        self.assertIn(
            "evidence",
            payload,
        )

        self.assertIn(
            "current_due_at",
            payload,
        )

        self.assertIn(
            "counterparty",
            payload,
        )
