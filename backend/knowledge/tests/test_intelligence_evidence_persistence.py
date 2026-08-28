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
    ApprovalItem,
)
from approvals.tasks import (
    analyze_new_approvals,
)

from inbox.models import (
    Conversation,
    InboxMessage,
    Organization,
)

from knowledge.models import (
    KnowledgeEvidence,
)

from knowledge.services.intelligence_evidence_builders import (
    build_action_evidence,
    build_approval_evidence,
    build_expected_response_evidence,
    build_followup_evidence,
)
from knowledge.services.intelligence_evidence_persistence import (
    persist_intelligence_evidence,
)


User = get_user_model()


class IntelligenceEvidencePersistenceTests(
    TestCase
):

    def setUp(self):
        self.user = User.objects.create_user(
            email="evidence-persist@test.com",
            password="pass123",
        )

        self.organization = (
            Organization.objects.create(
                name="Evidence Persistence",
                slug="evidence-persistence",
            )
        )

        self.conversation = (
            Conversation.objects.create(
                user=self.user,
                organization=self.organization,
                conversation_key=(
                    "evidence-persistence-thread"
                ),
                subject="Evidence",
            )
        )

        self.counter = 0

    def message(
        self,
        *,
        subject,
        body,
        direction="inbound",
    ):
        self.counter += 1

        return InboxMessage.objects.create(
            user=self.user,
            organization=self.organization,
            conversation=self.conversation,
            platform="gmail",
            direction=direction,
            external_message_id=(
                f"evidence-persist-{self.counter}"
            ),
            sender=(
                "customer@example.com"
                if direction == "inbound"
                else self.user.email
            ),
            recipients=(
                self.user.email
                if direction == "inbound"
                else "customer@example.com"
            ),
            subject=subject,
            body=body,
            received_at=datetime(
                2026,
                8,
                28,
                5,
                self.counter,
                tzinfo=dt_timezone.utc,
            ),
        )

    def test_deterministic_action_persists_exact_evidence(
        self,
    ):
        msg = self.message(
            subject="Quotation required",
            body=(
                "Please send the revised "
                "quotation by tomorrow."
            ),
        )

        analyze_new_messages.run(
            message_ids=[msg.id]
        )

        action = ActionItem.objects.get(
            message=msg
        )

        evidence = (
            build_action_evidence(
                action
            )
        )

        self.assertEqual(
            evidence.evidence_quality,
            "exact",
        )

        self.assertEqual(
            evidence.evidence_text,
            (
                "Please send the revised "
                "quotation by tomorrow."
            ),
        )

        self.assertEqual(
            evidence.processing_mode,
            "deterministic",
        )

    def test_deterministic_approval_persists_exact_evidence(
        self,
    ):
        msg = self.message(
            subject="Deployment",
            body=(
                "Please approve the "
                "production deployment."
            ),
        )

        analyze_new_approvals.run(
            message_ids=[msg.id]
        )

        approval = (
            ApprovalItem.objects.get(
                message=msg
            )
        )

        evidence = (
            build_approval_evidence(
                approval
            )
        )

        self.assertEqual(
            evidence.evidence_quality,
            "exact",
        )

        self.assertEqual(
            evidence.evidence_text,
            (
                "Please approve the "
                "production deployment."
            ),
        )

    def test_followup_persists_exact_evidence(
        self,
    ):
        msg = self.message(
            subject="Vendor",
            body=(
                "Please follow up with "
                "the vendor tomorrow."
            ),
        )

        analyze_new_followups.run(
            message_ids=[msg.id]
        )

        item = FollowUpItem.objects.get(
            last_message=msg
        )

        evidence = (
            build_followup_evidence(
                item
            )
        )

        self.assertEqual(
            evidence.evidence_quality,
            "exact",
        )

        self.assertEqual(
            evidence.evidence_text,
            (
                "Please follow up with "
                "the vendor tomorrow."
            ),
        )

    def test_expected_response_persists_exact_evidence(
        self,
    ):
        msg = self.message(
            subject="Vendor",
            body=(
                "Vendor will confirm tomorrow."
            ),
        )

        analyze_new_expected_responses.run(
            message_ids=[msg.id]
        )

        item = (
            ExpectedResponseItem.objects.get(
                source_message=msg
            )
        )

        evidence = (
            build_expected_response_evidence(
                item
            )
        )

        self.assertEqual(
            evidence.evidence_quality,
            "exact",
        )

        self.assertEqual(
            evidence.evidence_text,
            "Vendor will confirm tomorrow.",
        )

    def test_ai_action_preserves_cloud_provenance(
        self,
    ):
        msg = self.message(
            subject="Pricing",
            body=(
                "Please send the revised "
                "pricing tomorrow."
            ),
        )

        action = ActionItem.objects.create(
            user=self.user,
            organization=self.organization,
            message=msg,
            title="Send revised pricing",
            source_type="ai",
            confidence_score=98,
        )

        persist_intelligence_evidence(
            action,
            evidence_text=(
                "Please send the revised "
                "pricing tomorrow."
            ),
            extraction_method="ai",
            processing_mode="cloud",
            provider="openai",
            model="test-model",
            confidence=98,
        )

        evidence = (
            build_action_evidence(
                action
            )
        )

        self.assertEqual(
            evidence.evidence_quality,
            "exact",
        )

        self.assertEqual(
            evidence.processing_mode,
            "cloud",
        )

        self.assertEqual(
            evidence.provider,
            "openai",
        )

        self.assertEqual(
            evidence.model,
            "test-model",
        )

    def test_ai_approval_preserves_local_provenance(
        self,
    ):
        msg = self.message(
            subject="Deployment",
            body=(
                "Please approve deployment."
            ),
        )

        approval = (
            ApprovalItem.objects.create(
                user=self.user,
                organization=self.organization,
                message=msg,
                conversation=self.conversation,
                title="Authorize deployment",
                source_type="ai",
                confidence_score=97,
            )
        )

        persist_intelligence_evidence(
            approval,
            evidence_text=(
                "Please approve deployment."
            ),
            extraction_method="ai",
            processing_mode="local",
            provider="ollama",
            model="local-model",
            confidence=97,
        )

        evidence = (
            build_approval_evidence(
                approval
            )
        )

        self.assertEqual(
            evidence.processing_mode,
            "local",
        )

        self.assertEqual(
            evidence.provider,
            "ollama",
        )

        self.assertEqual(
            evidence.model,
            "local-model",
        )

    def test_same_source_persistence_is_idempotent(
        self,
    ):
        msg = self.message(
            subject="Pricing",
            body="Please send the quotation.",
        )

        action = ActionItem.objects.create(
            user=self.user,
            organization=self.organization,
            message=msg,
            title="Send quotation",
            source_type="email",
            confidence_score=80,
        )

        for _ in range(2):
            persist_intelligence_evidence(
                action,
                evidence_text=(
                    "Please send the quotation."
                ),
                extraction_method=(
                    "deterministic"
                ),
                processing_mode=(
                    "deterministic"
                ),
                confidence=80,
            )

        self.assertEqual(
            KnowledgeEvidence.objects.filter(
                organization=self.organization,
                message=msg,
                title=(
                    "ONEUCH-INTELLIGENCE:"
                    f"action:{action.id}"
                ),
            ).count(),
            1,
        )
