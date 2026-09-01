from django.contrib.auth import (
    get_user_model,
)
from django.test import TestCase
from django.utils import timezone

from actions.models import (
    ActionItem,
    ExpectedResponseItem,
    FollowUpItem,
)
from approvals.models import (
    ApprovalItem,
)
from inbox.models import (
    Conversation,
    InboxMessage,
    Organization,
)

from knowledge.services.intelligence_evidence import (
    IntelligenceEvidenceError,
)
from knowledge.services.intelligence_evidence_builders import (
    build_action_evidence,
    build_approval_evidence,
    build_expected_response_evidence,
    build_followup_evidence,
    build_intelligence_evidence,
)


User = get_user_model()


class IntelligenceEvidenceBuilderTests(
    TestCase
):

    def setUp(self):
        self.user = User.objects.create_user(
            email=(
                "evidence-builders@test.com"
            ),
            password="pass123",
        )

        self.organization = (
            Organization.objects.create(
                name=(
                    "Evidence Builder Test"
                ),
                slug=(
                    "evidence-builder-test"
                ),
            )
        )

        self.conversation = (
            Conversation.objects.create(
                user=self.user,
                organization=self.organization,
                conversation_key=(
                    "evidence-builder-thread"
                ),
                subject="Pricing",
            )
        )

        self.message = (
            InboxMessage.objects.create(
                user=self.user,
                organization=self.organization,
                conversation=self.conversation,
                platform="gmail",
                direction="inbound",
                external_message_id=(
                    "evidence-builder-001"
                ),
                sender=(
                    "customer@example.com"
                ),
                recipients=self.user.email,
                subject="Pricing",
                body=(
                    "Please send the revised "
                    "pricing tomorrow."
                ),
                received_at=timezone.now(),
            )
        )

    def test_action_is_source_only(
        self,
    ):
        action = ActionItem.objects.create(
            user=self.user,
            organization=(
                self.organization
            ),
            message=self.message,
            title="Send pricing",
            source_type="email",
            confidence_score=80,
        )

        evidence = (
            build_action_evidence(
                action
            )
        )

        self.assertEqual(
            evidence.object_type,
            "action",
        )

        self.assertEqual(
            evidence.evidence_quality,
            "source_only",
        )

        self.assertEqual(
            evidence.extraction_method,
            "deterministic",
        )

        self.assertEqual(
            evidence.processing_mode,
            "deterministic",
        )

        self.assertEqual(
            evidence.source_message_id,
            self.message.id,
        )

    def test_existing_ai_action_does_not_fabricate_provider(
        self,
    ):
        action = ActionItem.objects.create(
            user=self.user,
            organization=(
                self.organization
            ),
            message=self.message,
            title="AI detected work",
            source_type="ai",
            confidence_score=96,
        )

        evidence = (
            build_action_evidence(
                action
            )
        )

        self.assertEqual(
            evidence.extraction_method,
            "ai",
        )

        self.assertEqual(
            evidence.processing_mode,
            "unknown",
        )

        self.assertIsNone(
            evidence.provider
        )

        self.assertIsNone(
            evidence.model
        )

    def test_approval_is_source_only(
        self,
    ):
        approval = (
            ApprovalItem.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                message=self.message,
                conversation=(
                    self.conversation
                ),
                title=(
                    "Approve pricing"
                ),
                source_type="email",
                confidence_score=85,
            )
        )

        evidence = (
            build_approval_evidence(
                approval
            )
        )

        self.assertEqual(
            evidence.object_type,
            "approval",
        )

        self.assertEqual(
            evidence.evidence_quality,
            "source_only",
        )

        self.assertEqual(
            evidence.source_message_id,
            self.message.id,
        )

    def test_existing_ai_approval_keeps_unknown_ai_provenance(
        self,
    ):
        approval = (
            ApprovalItem.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                message=self.message,
                conversation=(
                    self.conversation
                ),
                title=(
                    "AI approval"
                ),
                source_type="ai",
                confidence_score=97,
            )
        )

        evidence = (
            build_approval_evidence(
                approval
            )
        )

        self.assertEqual(
            evidence.extraction_method,
            "ai",
        )

        self.assertEqual(
            evidence.processing_mode,
            "unknown",
        )

        self.assertIsNone(
            evidence.provider
        )

    def test_expected_response_has_exact_evidence(
        self,
    ):
        item = (
            ExpectedResponseItem
            .objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                conversation=(
                    self.conversation
                ),
                source_message=(
                    self.message
                ),
                evidence_text=(
                    "Please send the revised "
                    "pricing tomorrow."
                ),
                status="waiting",
            )
        )

        evidence = (
            build_expected_response_evidence(
                item
            )
        )

        self.assertEqual(
            evidence.object_type,
            "expected_response",
        )

        self.assertEqual(
            evidence.evidence_quality,
            "exact",
        )

        self.assertEqual(
            evidence.evidence_text,
            (
                "Please send the revised "
                "pricing tomorrow."
            ),
        )

        self.assertEqual(
            evidence.confidence,
            100,
        )

    def test_legacy_non_verbatim_expected_response_downgrades_to_source_only(
        self,
    ):
        item = (
            ExpectedResponseItem
            .objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                conversation=(
                    self.conversation
                ),
                source_message=(
                    self.message
                ),
                evidence_text=(
                    "Customer requested updated "
                    "commercial pricing."
                ),
                status="waiting",
            )
        )

        evidence = (
            build_expected_response_evidence(
                item
            )
        )

        self.assertEqual(
            evidence.object_type,
            "expected_response",
        )

        self.assertEqual(
            evidence.evidence_quality,
            "source_only",
        )

        self.assertEqual(
            evidence.evidence_text,
            "",
        )

        self.assertEqual(
            evidence.source_message_id,
            self.message.id,
        )

        self.assertEqual(
            item.evidence_text,
            (
                "Customer requested updated "
                "commercial pricing."
            ),
        )

    def test_expected_response_without_text_downgrades_to_source_only(
        self,
    ):
        item = (
            ExpectedResponseItem
            .objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                conversation=(
                    self.conversation
                ),
                source_message=(
                    self.message
                ),
                evidence_text="",
                status="waiting",
            )
        )

        evidence = (
            build_expected_response_evidence(
                item
            )
        )

        self.assertEqual(
            evidence.evidence_quality,
            "source_only",
        )

    def test_followup_is_source_only(
        self,
    ):
        item = (
            FollowUpItem.objects.create(
                user=self.user,
                organization=(
                    self.organization
                ),
                conversation=(
                    self.conversation
                ),
                last_message=(
                    self.message
                ),
                status="pending",
            )
        )

        evidence = (
            build_followup_evidence(
                item
            )
        )

        self.assertEqual(
            evidence.object_type,
            "followup",
        )

        self.assertEqual(
            evidence.evidence_quality,
            "source_only",
        )

        self.assertEqual(
            evidence.processing_mode,
            "deterministic",
        )

    def test_shared_dispatcher_routes_supported_objects(
        self,
    ):
        action = ActionItem.objects.create(
            user=self.user,
            organization=(
                self.organization
            ),
            message=self.message,
            title="Send pricing",
            source_type="email",
            confidence_score=80,
        )

        evidence = (
            build_intelligence_evidence(
                action
            )
        )

        self.assertEqual(
            evidence.object_type,
            "action",
        )

    def test_cross_tenant_action_is_rejected(
        self,
    ):
        other_organization = (
            Organization.objects.create(
                name="Other Organization",
                slug="other-org-evidence",
            )
        )

        action = ActionItem.objects.create(
            user=self.user,
            organization=(
                other_organization
            ),
            message=self.message,
            title="Invalid action",
            source_type="email",
            confidence_score=80,
        )

        with self.assertRaises(
            IntelligenceEvidenceError
        ):
            build_action_evidence(
                action
            )

    def test_unsaved_action_is_rejected(
        self,
    ):
        action = ActionItem(
            user=self.user,
            organization=(
                self.organization
            ),
            message=self.message,
            title="Unsaved",
            source_type="email",
            confidence_score=80,
        )

        with self.assertRaises(
            IntelligenceEvidenceError
        ):
            build_action_evidence(
                action
            )

    def test_unsupported_object_is_rejected(
        self,
    ):
        with self.assertRaises(
            IntelligenceEvidenceError
        ):
            build_intelligence_evidence(
                self.message
            )
