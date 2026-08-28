from dataclasses import (
    asdict,
    dataclass,
)
from typing import Optional


class IntelligenceEvidenceError(
    ValueError
):
    """
    Raised when intelligence evidence violates the
    One UCH evidence contract.
    """


@dataclass(frozen=True)
class IntelligenceEvidence:
    """
    Provider- and domain-neutral evidence contract for
    One UCH intelligence.

    This is intentionally NOT another database model.

    Existing and future intelligence domains expose this
    normalized representation so UI, audit, commitments,
    ownership, SLA and risk engines can explain:

        - what business object was created
        - which communication caused it
        - what exact/source evidence supports it
        - how it was detected
        - whether AI was involved
        - which provider/model was used
        - how confident One UCH is

    Persistence remains the responsibility of existing
    domain models and KnowledgeEvidence.
    """

    object_type: str
    object_id: int

    organization_id: int

    source_message_id: Optional[int]
    conversation_id: Optional[int]

    evidence_text: str

    extraction_method: str
    processing_mode: str

    provider: Optional[str]
    model: Optional[str]

    confidence: int

    evidence_quality: str = "exact"

    def to_dict(self):
        return asdict(
            self
        )


class IntelligenceEvidenceValidator:
    """
    Validate normalized intelligence evidence.

    Critical invariant:

    An evidence contract must never claim an exact quote
    unless that text actually exists in the source message.
    """

    EXTRACTION_METHODS = {
        "deterministic",
        "ai",
        "manual",
        "system",
    }

    PROCESSING_MODES = {
        "deterministic",
        "cloud",
        "local",
        "unknown",
    }

    EVIDENCE_QUALITIES = {
        "exact",
        "source_only",
        "none",
    }

    @classmethod
    def validate(
        cls,
        evidence,
        *,
        source_message=None,
    ):
        if not isinstance(
            evidence,
            IntelligenceEvidence,
        ):
            raise IntelligenceEvidenceError(
                "Evidence must be an "
                "IntelligenceEvidence instance."
            )

        object_type = (
            evidence.object_type or ""
        ).strip()

        if not object_type:
            raise IntelligenceEvidenceError(
                "object_type is required."
            )

        if (
            not isinstance(
                evidence.object_id,
                int,
            )
            or evidence.object_id <= 0
        ):
            raise IntelligenceEvidenceError(
                "object_id must be a positive integer."
            )

        if (
            not isinstance(
                evidence.organization_id,
                int,
            )
            or evidence.organization_id <= 0
        ):
            raise IntelligenceEvidenceError(
                "organization_id must be a "
                "positive integer."
            )

        if (
            evidence.extraction_method
            not in cls.EXTRACTION_METHODS
        ):
            raise IntelligenceEvidenceError(
                "Unsupported extraction_method."
            )

        if (
            evidence.processing_mode
            not in cls.PROCESSING_MODES
        ):
            raise IntelligenceEvidenceError(
                "Unsupported processing_mode."
            )

        if (
            evidence.evidence_quality
            not in cls.EVIDENCE_QUALITIES
        ):
            raise IntelligenceEvidenceError(
                "Unsupported evidence_quality."
            )

        if (
            not isinstance(
                evidence.confidence,
                int,
            )
            or evidence.confidence < 0
            or evidence.confidence > 100
        ):
            raise IntelligenceEvidenceError(
                "confidence must be an integer "
                "between 0 and 100."
            )

        # --------------------------------------------------
        # AI provenance
        # --------------------------------------------------

        if (
            evidence.extraction_method
            == "ai"
        ):
            if (
                evidence.processing_mode
                not in {
                    "cloud",
                    "local",
                    "unknown",
                }
            ):
                raise IntelligenceEvidenceError(
                    "AI evidence has invalid "
                    "processing_mode."
                )

        else:
            if (
                evidence.processing_mode
                not in {
                    "deterministic",
                    "unknown",
                }
            ):
                raise IntelligenceEvidenceError(
                    "Non-AI evidence cannot claim "
                    "cloud/local processing."
                )

        # --------------------------------------------------
        # Evidence quality semantics
        # --------------------------------------------------

        evidence_text = (
            evidence.evidence_text or ""
        ).strip()

        if (
            evidence.evidence_quality
            == "exact"
            and not evidence_text
        ):
            raise IntelligenceEvidenceError(
                "Exact evidence requires evidence_text."
            )

        if (
            evidence.evidence_quality
            == "none"
            and evidence_text
        ):
            raise IntelligenceEvidenceError(
                "Evidence quality 'none' cannot "
                "contain evidence_text."
            )

        # --------------------------------------------------
        # Optional source-message verification.
        # --------------------------------------------------

        if source_message is not None:

            if (
                evidence.source_message_id
                != source_message.id
            ):
                raise IntelligenceEvidenceError(
                    "Evidence source_message_id does "
                    "not match the supplied message."
                )

            if (
                evidence.organization_id
                != source_message.organization_id
            ):
                raise IntelligenceEvidenceError(
                    "Cross-tenant evidence is forbidden."
                )

            source_conversation_id = (
                source_message.conversation_id
            )

            if (
                evidence.conversation_id
                is not None
                and source_conversation_id
                != evidence.conversation_id
            ):
                raise IntelligenceEvidenceError(
                    "Evidence conversation does not "
                    "match the source message."
                )

            # Exact evidence must exist in the actual
            # source communication. Compare normalized
            # whitespace while preserving the original
            # evidence string in the contract.
            if (
                evidence.evidence_quality
                == "exact"
            ):
                source_text = cls._normalize(
                    " ".join(
                        [
                            source_message.subject
                            or "",
                            source_message.body
                            or "",
                        ]
                    )
                )

                normalized_evidence = (
                    cls._normalize(
                        evidence_text
                    )
                )

                if (
                    normalized_evidence
                    not in source_text
                ):
                    raise IntelligenceEvidenceError(
                        "Exact evidence text does not "
                        "exist in the source message."
                    )

        return evidence

    @staticmethod
    def _normalize(
        value,
    ):
        return " ".join(
            str(
                value or ""
            ).split()
        ).lower()
