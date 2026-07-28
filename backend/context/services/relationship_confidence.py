import logging

from django.utils import timezone

logger = logging.getLogger(__name__)

class RelationshipConfidenceEngine:
    """
    Calculates enterprise relationship confidence.
    """

    EVIDENCE_WEIGHTS = {

        "EMAIL": 2,

        "MEETING": 6,

        "APPROVAL": 7,

        "PAYMENT": 10,

        "CONTRACT": 15,

        "QUOTE": 5,

        "TASK": 3,

        "GENERAL": 1,
    }

    @classmethod
    def calculate(
        cls,
        *,
        relationship,
        evidence_type="GENERAL",
    ):

        base = cls.EVIDENCE_WEIGHTS.get(
            evidence_type,
            1,
        )

        interaction_bonus = min(
            relationship.evidence_count,
            50,
        )

        score = min(
            100,
            base + interaction_bonus,
        )

        return score

    @classmethod
    def update(
        cls,
        *,
        relationship,
        evidence_type="GENERAL",
    ):

        relationship.confidence = cls.calculate(
            relationship=relationship,
            evidence_type=evidence_type,
        )

        relationship.last_verified = timezone.now()

        relationship.save(
            update_fields=[
                "confidence",
                "last_verified",
                "updated_at",
            ]
        )

        logger.info(
            "Relationship confidence updated",
            extra={
                "relationship": relationship.id,
                "confidence": float(relationship.confidence),
                "evidence_type": evidence_type,
            },
        )

        return relationship