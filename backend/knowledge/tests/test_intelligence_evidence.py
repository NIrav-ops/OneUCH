from django.contrib.auth import (
    get_user_model,
)
from django.test import TestCase
from django.utils import timezone

from inbox.models import (
    Conversation,
    InboxMessage,
    Organization,
)

from knowledge.services.intelligence_evidence import (
    IntelligenceEvidence,
    IntelligenceEvidenceError,
    IntelligenceEvidenceValidator,
)


User = get_user_model()


class IntelligenceEvidenceContractTests(
    TestCase
):

    def setUp(self):
        self.user = User.objects.create_user(
            email="evidence-contract@test.com",
            password="pass123",
        )

        self.organization = (
            Organization.objects.create(
                name="Evidence Contract Test",
                slug="evidence-contract-test",
            )
        )

        self.conversation = (
            Conversation.objects.create(
                user=self.user,
                organization=self.organization,
                conversation_key=(
                    "evidence-contract-thread"
                ),
                subject="Quotation",
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
                    "evidence-contract-001"
                ),
                sender=(
                    "customer@example.com"
                ),
                recipients=self.user.email,
                subject="Revised quotation",
                body=(
                    "Please send the revised "
                    "quotation tomorrow."
                ),
                received_at=timezone.now(),
            )
        )

    def _evidence(
        self,
        **overrides,
    ):
        payload = {
            "object_type": "action",
            "object_id": 42,
            "organization_id": (
                self.organization.id
            ),
            "source_message_id": (
                self.message.id
            ),
            "conversation_id": (
                self.conversation.id
            ),
            "evidence_text": (
                "Please send the revised "
                "quotation tomorrow."
            ),
            "extraction_method":
                "deterministic",
            "processing_mode":
                "deterministic",
            "provider": None,
            "model": None,
            "confidence": 100,
            "evidence_quality": "exact",
        }

        payload.update(
            overrides
        )

        return IntelligenceEvidence(
            **payload
        )

    def test_valid_exact_evidence(
        self,
    ):
        evidence = self._evidence()

        result = (
            IntelligenceEvidenceValidator
            .validate(
                evidence,
                source_message=(
                    self.message
                ),
            )
        )

        self.assertEqual(
            result,
            evidence,
        )

    def test_to_dict_preserves_contract(
        self,
    ):
        payload = (
            self._evidence()
            .to_dict()
        )

        self.assertEqual(
            payload[
                "object_type"
            ],
            "action",
        )

        self.assertEqual(
            payload[
                "source_message_id"
            ],
            self.message.id,
        )

        self.assertEqual(
            payload[
                "evidence_quality"
            ],
            "exact",
        )

    def test_hallucinated_exact_evidence_is_rejected(
        self,
    ):
        evidence = self._evidence(
            evidence_text=(
                "Please approve production."
            )
        )

        with self.assertRaises(
            IntelligenceEvidenceError
        ):
            (
                IntelligenceEvidenceValidator
                .validate(
                    evidence,
                    source_message=(
                        self.message
                    ),
                )
            )

    def test_cross_tenant_evidence_is_rejected(
        self,
    ):
        other_organization = (
            Organization.objects.create(
                name="Other Tenant",
                slug="other-tenant",
            )
        )

        evidence = self._evidence(
            organization_id=(
                other_organization.id
            )
        )

        with self.assertRaises(
            IntelligenceEvidenceError
        ):
            (
                IntelligenceEvidenceValidator
                .validate(
                    evidence,
                    source_message=(
                        self.message
                    ),
                )
            )

    def test_source_only_does_not_claim_exact_quote(
        self,
    ):
        evidence = self._evidence(
            evidence_text="",
            evidence_quality=(
                "source_only"
            ),
        )

        result = (
            IntelligenceEvidenceValidator
            .validate(
                evidence,
                source_message=(
                    self.message
                ),
            )
        )

        self.assertEqual(
            result.evidence_quality,
            "source_only",
        )

    def test_ai_cloud_provenance_is_valid(
        self,
    ):
        evidence = self._evidence(
            extraction_method="ai",
            processing_mode="cloud",
            provider="openai",
            model="test-model",
            confidence=96,
        )

        result = (
            IntelligenceEvidenceValidator
            .validate(
                evidence,
                source_message=(
                    self.message
                ),
            )
        )

        self.assertEqual(
            result.processing_mode,
            "cloud",
        )

        self.assertEqual(
            result.provider,
            "openai",
        )

    def test_ai_local_provenance_is_valid(
        self,
    ):
        evidence = self._evidence(
            extraction_method="ai",
            processing_mode="local",
            provider="ollama",
            model="local-model",
            confidence=95,
        )

        result = (
            IntelligenceEvidenceValidator
            .validate(
                evidence,
                source_message=(
                    self.message
                ),
            )
        )

        self.assertEqual(
            result.processing_mode,
            "local",
        )

    def test_non_ai_cannot_claim_cloud_processing(
        self,
    ):
        evidence = self._evidence(
            extraction_method=(
                "deterministic"
            ),
            processing_mode="cloud",
        )

        with self.assertRaises(
            IntelligenceEvidenceError
        ):
            (
                IntelligenceEvidenceValidator
                .validate(
                    evidence,
                    source_message=(
                        self.message
                    ),
                )
            )

    def test_confidence_outside_range_is_rejected(
        self,
    ):
        evidence = self._evidence(
            confidence=101,
        )

        with self.assertRaises(
            IntelligenceEvidenceError
        ):
            (
                IntelligenceEvidenceValidator
                .validate(
                    evidence,
                    source_message=(
                        self.message
                    ),
                )
            )

    def test_exact_evidence_requires_text(
        self,
    ):
        evidence = self._evidence(
            evidence_text="",
        )

        with self.assertRaises(
            IntelligenceEvidenceError
        ):
            (
                IntelligenceEvidenceValidator
                .validate(
                    evidence,
                    source_message=(
                        self.message
                    ),
                )
            )

    def test_none_quality_requires_empty_text(
        self,
    ):
        evidence = self._evidence(
            evidence_quality="none",
        )

        with self.assertRaises(
            IntelligenceEvidenceError
        ):
            (
                IntelligenceEvidenceValidator
                .validate(
                    evidence,
                    source_message=(
                        self.message
                    ),
                )
            )
