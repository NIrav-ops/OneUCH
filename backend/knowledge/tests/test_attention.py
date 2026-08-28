from datetime import (
    datetime,
    timedelta,
    timezone as dt_timezone,
)

from django.contrib.auth import (
    get_user_model,
)
from django.test import TestCase

from rest_framework.test import APIClient

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

from knowledge.services.attention import (
    AttentionService,
)
from knowledge.services.communication_sla import (
    CommunicationSLAPolicy,
)
from knowledge.services.intelligence_evidence_persistence import (
    persist_intelligence_evidence,
)


User = get_user_model()


class AttentionServiceTests(
    TestCase
):

    def setUp(self):
        self.user = User.objects.create_user(
            email="owner@attention.test",
            password="pass123",
        )

        self.organization = (
            Organization.objects.create(
                name="Attention Org",
                slug="attention-org",
            )
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=self.organization,
            role="member",
        )

        self.other_organization = (
            Organization.objects.create(
                name="Other Attention Org",
                slug="other-attention-org",
            )
        )

        self.conversation = (
            Conversation.objects.create(
                user=self.user,
                organization=self.organization,
                conversation_key=(
                    "attention-thread"
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
        received_at=None,
        body=(
            "Please provide revised pricing."
        ),
        sender="customer@example.com",
    ):
        self.counter += 1

        return InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            platform="gmail",
            direction="inbound",
            external_message_id=(
                "attention-message-"
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
        owner=None,
        due_at=None,
        received_at=None,
        status="open",
        completed_at=None,
    ):
        msg = self.message(
            received_at=received_at
        )

        return ActionItem.objects.create(
            user=self.user,
            organization=self.organization,
            message=msg,
            title=(
                "Provide revised pricing "
                f"{self.counter}"
            ),
            owner=owner,
            due_date=due_at,
            status=status,
            completed_at=completed_at,
            source_type="email",
            confidence_score=80,
        )

    def test_dropped_ball_dominates_duplicate_signals(
        self,
    ):
        self.action(
            owner=None,
            due_at=(
                self.started_at
                + timedelta(
                    hours=3
                )
            ),
        )

        items = AttentionService.build(
            organization=self.organization,
            now=(
                self.started_at
                + timedelta(
                    hours=5
                )
            ),
            sla_policy=self.policy,
        )

        self.assertEqual(
            len(items),
            1,
        )

        item = items[0]

        self.assertEqual(
            item.category,
            "dropped_ball",
        )

        self.assertEqual(
            item.severity,
            "critical",
        )

        self.assertIn(
            "COMMUNICATION_SLA_BREACHED",
            item.signal_codes,
        )

        self.assertIn(
            "COMMITMENT_DEADLINE_OVERDUE",
            item.signal_codes,
        )

        self.assertIn(
            "NO_EXPLICIT_OWNER",
            item.signal_codes,
        )

    def test_sla_at_risk_dominates_ownership_gap(
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

        items = AttentionService.build(
            organization=self.organization,
            now=(
                self.started_at
                + timedelta(
                    hours=3,
                    minutes=30,
                )
            ),
            sla_policy=self.policy,
        )

        self.assertEqual(
            len(items),
            1,
        )

        item = items[0]

        self.assertEqual(
            item.category,
            "sla_at_risk",
        )

        self.assertEqual(
            item.severity,
            "high",
        )

        self.assertEqual(
            item.ownership_reason_code,
            "NO_EXPLICIT_OWNER",
        )

        self.assertIn(
            "COMMUNICATION_SLA_AT_RISK",
            item.signal_codes,
        )

        self.assertIn(
            "NO_EXPLICIT_OWNER",
            item.signal_codes,
        )

    def test_ownership_gap_alone_is_medium_attention(
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

        items = AttentionService.build(
            organization=self.organization,
            now=(
                self.started_at
                + timedelta(
                    hours=2
                )
            ),
            sla_policy=self.policy,
        )

        self.assertEqual(
            len(items),
            1,
        )

        self.assertEqual(
            items[0].category,
            "ownership_gap",
        )

        self.assertEqual(
            items[0].severity,
            "medium",
        )

    def test_on_track_valid_owner_has_no_attention(
        self,
    ):
        self.action(
            owner=self.user,
            due_at=(
                self.started_at
                + timedelta(
                    hours=24
                )
            ),
        )

        items = AttentionService.build(
            organization=self.organization,
            now=(
                self.started_at
                + timedelta(
                    hours=2
                )
            ),
            sla_policy=self.policy,
        )

        self.assertEqual(
            items,
            [],
        )

    def test_counterparty_overdue_is_high_attention(
        self,
    ):
        msg = self.message(
            body=(
                "We will provide pricing today."
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
                "We will provide pricing today."
            ),
            response_due_at=(
                self.started_at
                + timedelta(
                    hours=2
                )
            ),
            status="waiting",
        )

        items = AttentionService.build(
            organization=self.organization,
            now=(
                self.started_at
                + timedelta(
                    hours=3
                )
            ),
            sla_policy=self.policy,
        )

        self.assertEqual(
            len(items),
            1,
        )

        item = items[0]

        self.assertEqual(
            item.category,
            "dropped_ball",
        )

        self.assertEqual(
            item.severity,
            "high",
        )

        self.assertEqual(
            item.responsibility_side,
            "counterparty",
        )

    def test_fulfilled_commitment_disappears_from_attention(
        self,
    ):
        self.action(
            owner=self.user,
            status="completed",
            completed_at=(
                self.started_at
                + timedelta(
                    hours=5
                )
            ),
            due_at=(
                self.started_at
                + timedelta(
                    hours=1
                )
            ),
        )

        items = AttentionService.build(
            organization=self.organization,
            now=(
                self.started_at
                + timedelta(
                    hours=6
                )
            ),
            sla_policy=self.policy,
        )

        self.assertEqual(
            items,
            [],
        )

    def test_summary_counts_current_attention(
        self,
    ):
        self.action(
            owner=None,
            due_at=(
                self.started_at
                + timedelta(
                    hours=3
                )
            ),
        )

        payload = (
            AttentionService
            .build_payload(
                organization=self.organization,
                now=(
                    self.started_at
                    + timedelta(
                        hours=5
                    )
                ),
                sla_policy=self.policy,
            )
        )

        self.assertEqual(
            payload["summary"]["total"],
            1,
        )

        self.assertEqual(
            payload["summary"]["critical"],
            1,
        )

        self.assertEqual(
            payload["summary"]["dropped_ball"],
            1,
        )

        self.assertEqual(
            payload["summary"]["internal"],
            1,
        )

    def test_exact_evidence_is_preserved(
        self,
    ):
        action = self.action(
            owner=None,
            due_at=(
                self.started_at
                + timedelta(
                    hours=24
                )
            ),
        )

        persist_intelligence_evidence(
            action,
            evidence_text=(
                "Please provide revised pricing."
            ),
            extraction_method="deterministic",
            processing_mode="deterministic",
            confidence=80,
        )

        item = AttentionService.build(
            organization=self.organization,
            now=(
                self.started_at
                + timedelta(
                    hours=2
                )
            ),
            sla_policy=self.policy,
        )[0]

        self.assertEqual(
            item.evidence[
                "evidence_quality"
            ],
            "exact",
        )

        self.assertEqual(
            item.evidence[
                "evidence_text"
            ],
            (
                "Please provide revised pricing."
            ),
        )

    def test_organization_isolation(
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

        items = AttentionService.build(
            organization=(
                self.other_organization
            ),
            now=(
                self.started_at
                + timedelta(
                    hours=5
                )
            ),
            sla_policy=self.policy,
        )

        self.assertEqual(
            items,
            [],
        )


class AttentionAPITests(
    TestCase
):

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            email="api@attention.test",
            password="pass123",
        )

        self.organization = (
            Organization.objects.create(
                name="Attention API Org",
                slug="attention-api-org",
            )
        )

        OrganizationUser.objects.create(
            user=self.user,
            organization=self.organization,
            role="member",
        )

        self.conversation = (
            Conversation.objects.create(
                user=self.user,
                organization=self.organization,
                conversation_key=(
                    "attention-api-thread"
                ),
                subject="API Pricing",
            )
        )

    def test_attention_api_requires_authentication(
        self,
    ):
        response = self.client.get(
            "/api/knowledge/attention/"
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_attention_api_requires_active_membership(
        self,
    ):
        outsider = User.objects.create_user(
            email="outsider@attention.test",
            password="pass123",
        )

        self.client.force_authenticate(
            user=outsider
        )

        response = self.client.get(
            "/api/knowledge/attention/"
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_attention_api_returns_tenant_scoped_payload(
        self,
    ):
        now = (
            __import__(
                "django.utils.timezone",
                fromlist=["now"],
            )
            .now()
        )

        msg = InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            platform="gmail",
            direction="inbound",
            external_message_id=(
                "attention-api-message"
            ),
            sender="customer@example.com",
            recipients=self.user.email,
            subject="Pricing",
            body=(
                "Please provide revised pricing."
            ),
            received_at=(
                now
                - timedelta(
                    hours=5
                )
            ),
        )

        ActionItem.objects.create(
            user=self.user,
            organization=self.organization,
            message=msg,
            title="Provide revised pricing",
            owner=None,
            status="open",
            source_type="email",
            due_date=(
                now
                - timedelta(
                    hours=1
                )
            ),
            confidence_score=80,
        )

        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.get(
            "/api/knowledge/attention/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data[
                "organization_id"
            ],
            self.organization.id,
        )

        self.assertEqual(
            response.data[
                "summary"
            ]["total"],
            1,
        )

        self.assertEqual(
            response.data[
                "items"
            ][0]["category"],
            "dropped_ball",
        )

        self.assertEqual(
            response.data[
                "items"
            ][0]["responsibility_side"],
            "internal",
        )
