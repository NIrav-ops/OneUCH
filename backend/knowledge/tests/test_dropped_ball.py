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
    OrganizationUser,
)

from knowledge.services.communication_sla import (
    CommunicationSLAPolicy,
)
from knowledge.services.dropped_ball import (
    DroppedBallService,
)
from knowledge.services.intelligence_evidence_persistence import (
    persist_intelligence_evidence,
)


User = get_user_model()


class DroppedBallServiceTests(
    TestCase
):

    def setUp(self):
        self.user = User.objects.create_user(
            email="owner@dropped.test",
            password="pass123",
        )

        self.organization = (
            Organization.objects.create(
                name="Dropped Ball Org",
                slug="dropped-ball-org",
            )
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=self.organization,
            role="member",
        )

        self.other_organization = (
            Organization.objects.create(
                name="Other Dropped Ball Org",
                slug="other-dropped-ball-org",
            )
        )

        self.conversation = (
            Conversation.objects.create(
                user=self.user,
                organization=self.organization,
                conversation_key=(
                    "dropped-ball-thread"
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
        recipients=None,
        received_at=None,
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
                "dropped-message-"
                f"{self.counter}"
            ),
            sender=sender,
            recipients=recipients,
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
        owner=None,
        status="open",
        due_at=None,
        completed_at=None,
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
            due_date=due_at,
            completed_at=completed_at,
            confidence_score=80,
        )

    def test_sla_breach_creates_internal_dropped_ball(
        self,
    ):
        action = self.action(
            owner=self.user,
            due_at=(
                self.started_at
                + timedelta(
                    hours=24
                )
            ),
        )

        findings = (
            DroppedBallService.build(
                organization=(
                    self.organization
                ),
                sla_policy=self.policy,
                now=(
                    self.started_at
                    + timedelta(
                        hours=5
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
            finding.source_object_id,
            action.id,
        )

        self.assertEqual(
            finding.responsibility_side,
            "internal",
        )

        self.assertEqual(
            finding.reason_code,
            (
                "INTERNAL_COMMUNICATION_SLA_BREACHED"
            ),
        )

        self.assertIn(
            "COMMUNICATION_SLA_BREACHED",
            finding.signal_codes,
        )

    def test_commitment_deadline_breach_creates_dropped_ball(
        self,
    ):
        self.action(
            owner=self.user,
            due_at=(
                self.started_at
                + timedelta(
                    hours=1
                )
            ),
        )

        finding = (
            DroppedBallService.build(
                organization=(
                    self.organization
                ),
                sla_policy=self.policy,
                now=(
                    self.started_at
                    + timedelta(
                        hours=2
                    )
                ),
            )[0]
        )

        self.assertEqual(
            finding.reason_code,
            (
                "INTERNAL_COMMITMENT_DEADLINE_MISSED"
            ),
        )

        self.assertEqual(
            finding.sla_state,
            "on_track",
        )

        self.assertIn(
            "COMMITMENT_DEADLINE_OVERDUE",
            finding.signal_codes,
        )

    def test_sla_and_deadline_breach_are_combined(
        self,
    ):
        self.action(
            owner=self.user,
            due_at=(
                self.started_at
                + timedelta(
                    hours=3
                )
            ),
        )

        finding = (
            DroppedBallService.build(
                organization=(
                    self.organization
                ),
                sla_policy=self.policy,
                now=(
                    self.started_at
                    + timedelta(
                        hours=5
                    )
                ),
            )[0]
        )

        self.assertEqual(
            finding.reason_code,
            (
                "INTERNAL_SLA_AND_COMMITMENT_DEADLINE_MISSED"
            ),
        )

        self.assertIn(
            "COMMUNICATION_SLA_BREACHED",
            finding.signal_codes,
        )

        self.assertIn(
            "COMMITMENT_DEADLINE_OVERDUE",
            finding.signal_codes,
        )

    def test_ownership_gap_is_contributing_signal(
        self,
    ):
        self.action(
            owner=None,
            due_at=(
                self.started_at
                + timedelta(
                    hours=24
                )
            ),
        )

        finding = (
            DroppedBallService.build(
                organization=(
                    self.organization
                ),
                sla_policy=self.policy,
                now=(
                    self.started_at
                    + timedelta(
                        hours=5
                    )
                ),
            )[0]
        )

        self.assertEqual(
            finding.ownership_gap_type,
            "unassigned",
        )

        self.assertEqual(
            finding.ownership_reason_code,
            "NO_EXPLICIT_OWNER",
        )

        self.assertIn(
            "NO_EXPLICIT_OWNER",
            finding.signal_codes,
        )

    def test_ownership_gap_alone_is_not_dropped_ball(
        self,
    ):
        self.action(
            owner=None,
            due_at=(
                self.started_at
                + timedelta(
                    hours=24
                )
            ),
        )

        findings = (
            DroppedBallService.build(
                organization=(
                    self.organization
                ),
                sla_policy=self.policy,
                now=(
                    self.started_at
                    + timedelta(
                        hours=2
                    )
                ),
            )
        )

        self.assertEqual(
            findings,
            [],
        )

    def test_fulfilled_commitment_is_not_current_dropped_ball(
        self,
    ):
        self.action(
            owner=self.user,
            status="completed",
            due_at=(
                self.started_at
                + timedelta(
                    hours=1
                )
            ),
            completed_at=(
                self.started_at
                + timedelta(
                    hours=5
                )
            ),
        )

        findings = (
            DroppedBallService.build(
                organization=(
                    self.organization
                ),
                sla_policy=self.policy,
                now=(
                    self.started_at
                    + timedelta(
                        hours=6
                    )
                ),
            )
        )

        self.assertEqual(
            findings,
            [],
        )

    def test_counterparty_overdue_response_is_distinguished(
        self,
    ):
        msg = self.message(
            body=(
                "We will provide pricing tomorrow."
            ),
            sender="vendor@example.com",
        )

        item = (
            ExpectedResponseItem.objects.create(
                user=self.user,
                organization=self.organization,
                conversation=self.conversation,
                source_message=msg,
                expected_from=(
                    "vendor@example.com"
                ),
                evidence_text=(
                    "We will provide pricing tomorrow."
                ),
                response_due_at=(
                    self.started_at
                    + timedelta(
                        hours=2
                    )
                ),
                status="waiting",
            )
        )

        finding = (
            DroppedBallService.build(
                organization=(
                    self.organization
                ),
                sla_policy=self.policy,
                now=(
                    self.started_at
                    + timedelta(
                        hours=3
                    )
                ),
            )[0]
        )

        self.assertEqual(
            finding.source_object_id,
            item.id,
        )

        self.assertEqual(
            finding.responsibility_side,
            "counterparty",
        )

        self.assertEqual(
            finding.reason_code,
            "COUNTERPARTY_RESPONSE_OVERDUE",
        )

        self.assertIsNone(
            finding.sla_due_at
        )

    def test_future_counterparty_response_is_not_dropped_ball(
        self,
    ):
        msg = self.message(
            body=(
                "We will provide pricing tomorrow."
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
                "We will provide pricing tomorrow."
            ),
            response_due_at=(
                self.started_at
                + timedelta(
                    hours=5
                )
            ),
            status="waiting",
        )

        findings = (
            DroppedBallService.build(
                organization=(
                    self.organization
                ),
                sla_policy=self.policy,
                now=(
                    self.started_at
                    + timedelta(
                        hours=3
                    )
                ),
            )
        )

        self.assertEqual(
            findings,
            [],
        )

    def test_received_counterparty_response_clears_dropped_ball(
        self,
    ):
        msg = self.message(
            body=(
                "We will provide pricing tomorrow."
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
                "We will provide pricing tomorrow."
            ),
            response_due_at=(
                self.started_at
                + timedelta(
                    hours=2
                )
            ),
            status="received",
            resolved_at=(
                self.started_at
                + timedelta(
                    hours=3
                )
            ),
        )

        findings = (
            DroppedBallService.build(
                organization=(
                    self.organization
                ),
                sla_policy=self.policy,
                now=(
                    self.started_at
                    + timedelta(
                        hours=4
                    )
                ),
            )
        )

        self.assertEqual(
            findings,
            [],
        )

    def test_exact_evidence_is_preserved(
        self,
    ):
        action = self.action(
            owner=self.user,
            due_at=(
                self.started_at
                + timedelta(
                    hours=1
                )
            ),
        )

        persist_intelligence_evidence(
            action,
            evidence_text=(
                "Please provide revised "
                "pricing."
            ),
            extraction_method="deterministic",
            processing_mode="deterministic",
            confidence=80,
        )

        finding = (
            DroppedBallService.build(
                organization=(
                    self.organization
                ),
                sla_policy=self.policy,
                now=(
                    self.started_at
                    + timedelta(
                        hours=2
                    )
                ),
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

    def test_organization_isolation(
        self,
    ):
        self.action(
            owner=self.user,
            due_at=(
                self.started_at
                + timedelta(
                    hours=1
                )
            ),
        )

        findings = (
            DroppedBallService.build(
                organization=(
                    self.other_organization
                ),
                sla_policy=self.policy,
                now=(
                    self.started_at
                    + timedelta(
                        hours=5
                    )
                ),
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
            owner=None,
            due_at=(
                self.started_at
                + timedelta(
                    hours=1
                )
            ),
        )

        finding = (
            DroppedBallService.build(
                organization=(
                    self.organization
                ),
                sla_policy=self.policy,
                now=(
                    self.started_at
                    + timedelta(
                        hours=5
                    )
                ),
            )[0]
        )

        payload = finding.to_dict()

        self.assertIn(
            "signal_codes",
            payload,
        )

        self.assertIn(
            "evidence",
            payload,
        )

        self.assertIn(
            "responsibility_side",
            payload,
        )

        self.assertIn(
            "sla_state",
            payload,
        )

        self.assertIn(
            "ownership_reason_code",
            payload,
        )
