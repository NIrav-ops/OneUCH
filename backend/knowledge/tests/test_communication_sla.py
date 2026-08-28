from datetime import (
    datetime,
    timedelta,
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

from knowledge.services.communication_sla import (
    CommunicationSLAPolicy,
    CommunicationSLAService,
)
from knowledge.services.intelligence_evidence_persistence import (
    persist_intelligence_evidence,
)


User = get_user_model()


class CommunicationSLAServiceTests(
    TestCase
):

    def setUp(self):
        self.user = User.objects.create_user(
            email="sla-owner@test.com",
            password="pass123",
        )

        self.organization = (
            Organization.objects.create(
                name="SLA Org",
                slug="sla-org",
            )
        )

        self.other_organization = (
            Organization.objects.create(
                name="Other SLA Org",
                slug="other-sla-org",
            )
        )

        self.conversation = (
            Conversation.objects.create(
                user=self.user,
                organization=self.organization,
                conversation_key=(
                    "sla-thread"
                ),
                subject="Pricing",
            )
        )

        self.started_at = datetime(
            2026,
            8,
            28,
            8,
            0,
            tzinfo=dt_timezone.utc,
        )

        self.policy = (
            CommunicationSLAPolicy(
                target_minutes=240,
                at_risk_minutes=60,
            )
        )

        self.counter = 0

    def message(
        self,
        *,
        body,
        direction="inbound",
        sender=None,
        received_at=None,
    ):
        self.counter += 1

        if sender is None:
            sender = (
                "customer@example.com"
                if direction == "inbound"
                else self.user.email
            )

        return InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            platform="gmail",
            direction=direction,
            external_message_id=(
                "sla-message-"
                f"{self.counter}"
            ),
            sender=sender,
            recipients=self.user.email,
            subject="Pricing",
            body=body,
            received_at=(
                received_at
                or self.started_at
            ),
        )

    def action(
        self,
        *,
        status="open",
        completed_at=None,
        owner=None,
    ):
        msg = self.message(
            body=(
                "Please provide revised "
                "pricing."
            )
        )

        return ActionItem.objects.create(
            user=self.user,
            organization=self.organization,
            message=msg,
            title="Provide revised pricing",
            owner=owner,
            status=status,
            source_type="email",
            due_date=(
                self.started_at
                + timedelta(
                    hours=24
                )
            ),
            completed_at=(
                completed_at
            ),
            confidence_score=80,
        )

    def test_pending_commitment_is_on_track(
        self,
    ):
        self.action()

        findings = (
            CommunicationSLAService.build(
                organization=(
                    self.organization
                ),
                policy=self.policy,
                now=(
                    self.started_at
                    + timedelta(
                        hours=2
                    )
                ),
            )
        )

        self.assertEqual(
            len(findings),
            1,
        )

        finding = findings[0]

        self.assertEqual(
            finding.state,
            "on_track",
        )

        self.assertEqual(
            finding.reason_code,
            (
                "COMMUNICATION_SLA_ON_TRACK"
            ),
        )

        self.assertEqual(
            finding.seconds_remaining,
            7200,
        )

    def test_pending_commitment_becomes_at_risk(
        self,
    ):
        self.action()

        finding = (
            CommunicationSLAService.build(
                organization=(
                    self.organization
                ),
                policy=self.policy,
                now=(
                    self.started_at
                    + timedelta(
                        hours=3,
                        minutes=30,
                    )
                ),
            )[0]
        )

        self.assertEqual(
            finding.state,
            "at_risk",
        )

        self.assertEqual(
            finding.reason_code,
            (
                "COMMUNICATION_SLA_AT_RISK"
            ),
        )

        self.assertEqual(
            finding.seconds_remaining,
            1800,
        )

    def test_pending_commitment_becomes_breached(
        self,
    ):
        self.action()

        finding = (
            CommunicationSLAService.build(
                organization=(
                    self.organization
                ),
                policy=self.policy,
                now=(
                    self.started_at
                    + timedelta(
                        hours=5
                    )
                ),
            )[0]
        )

        self.assertEqual(
            finding.state,
            "breached",
        )

        self.assertEqual(
            finding.reason_code,
            (
                "COMMUNICATION_SLA_BREACHED"
            ),
        )

        self.assertEqual(
            finding.breached_by_seconds,
            3600,
        )

    def test_fulfilled_inside_sla_is_met(
        self,
    ):
        completed_at = (
            self.started_at
            + timedelta(
                hours=2
            )
        )

        self.action(
            status="completed",
            completed_at=(
                completed_at
            ),
        )

        finding = (
            CommunicationSLAService.build(
                organization=(
                    self.organization
                ),
                policy=self.policy,
                now=(
                    self.started_at
                    + timedelta(
                        hours=6
                    )
                ),
            )[0]
        )

        self.assertEqual(
            finding.state,
            "met",
        )

        self.assertEqual(
            finding.fulfilled_at,
            completed_at,
        )

    def test_fulfilled_after_sla_preserves_breach(
        self,
    ):
        completed_at = (
            self.started_at
            + timedelta(
                hours=5
            )
        )

        self.action(
            status="completed",
            completed_at=(
                completed_at
            ),
        )

        finding = (
            CommunicationSLAService.build(
                organization=(
                    self.organization
                ),
                policy=self.policy,
                now=(
                    self.started_at
                    + timedelta(
                        hours=6
                    )
                ),
            )[0]
        )

        self.assertEqual(
            finding.state,
            "breached",
        )

        self.assertEqual(
            finding.reason_code,
            (
                "COMMUNICATION_SLA_BREACHED_LATE"
            ),
        )

        self.assertEqual(
            finding.breached_by_seconds,
            3600,
        )

    def test_sla_clock_starts_from_message_received_at(
        self,
    ):
        self.action()

        finding = (
            CommunicationSLAService.build(
                organization=(
                    self.organization
                ),
                policy=self.policy,
                now=(
                    self.started_at
                    + timedelta(
                        minutes=30
                    )
                ),
            )[0]
        )

        self.assertEqual(
            finding.sla_started_at,
            self.started_at,
        )

        self.assertEqual(
            finding.sla_due_at,
            (
                self.started_at
                + timedelta(
                    hours=4
                )
            ),
        )

    def test_commitment_due_and_sla_due_remain_distinct(
        self,
    ):
        self.action()

        finding = (
            CommunicationSLAService.build(
                organization=(
                    self.organization
                ),
                policy=self.policy,
                now=self.started_at,
            )[0]
        )

        self.assertEqual(
            finding.commitment_due_at,
            (
                self.started_at
                + timedelta(
                    hours=24
                )
            ),
        )

        self.assertEqual(
            finding.sla_due_at,
            (
                self.started_at
                + timedelta(
                    hours=4
                )
            ),
        )

    def test_ignored_and_cancelled_commitments_are_excluded(
        self,
    ):
        self.action(
            status="ignored"
        )

        self.action(
            status="cancelled"
        )

        findings = (
            CommunicationSLAService.build(
                organization=(
                    self.organization
                ),
                policy=self.policy,
                now=(
                    self.started_at
                    + timedelta(
                        hours=10
                    )
                ),
            )
        )

        self.assertEqual(
            findings,
            [],
        )

    def test_they_owe_us_does_not_create_communication_sla(
        self,
    ):
        msg = self.message(
            body=(
                "Vendor will confirm tomorrow."
            ),
            sender="vendor@example.com",
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
            CommunicationSLAService.build(
                organization=(
                    self.organization
                ),
                policy=self.policy,
                now=(
                    self.started_at
                    + timedelta(
                        hours=10
                    )
                ),
            )
        )

        self.assertEqual(
            findings,
            [],
        )

    def test_finding_preserves_evidence_and_tenant_scope(
        self,
    ):
        action = self.action()

        persist_intelligence_evidence(
            action,
            evidence_text=(
                "Please provide revised "
                "pricing."
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
            CommunicationSLAService.build(
                organization=(
                    self.organization
                ),
                policy=self.policy,
                now=self.started_at,
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
                "pricing."
            ),
        )

        other_findings = (
            CommunicationSLAService.build(
                organization=(
                    self.other_organization
                ),
                policy=self.policy,
                now=self.started_at,
            )
        )

        self.assertEqual(
            other_findings,
            [],
        )

        payload = finding.to_dict()

        self.assertEqual(
            payload[
                "policy_target_minutes"
            ],
            240,
        )

        self.assertIn(
            "sla_due_at",
            payload,
        )

        self.assertIn(
            "commitment_due_at",
            payload,
        )
