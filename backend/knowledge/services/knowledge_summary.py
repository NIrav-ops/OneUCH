"""
Enterprise Knowledge Summary Service
"""

from django.db.models import Avg

from knowledge.models import (
    KnowledgeFact,
    KnowledgeEvidence,
)


class KnowledgeSummaryService:
    """
    Builds a knowledge summary for a BusinessObject.
    """

    def build(
        self,
        *,
        business_object,
    ):

        facts = KnowledgeFact.objects.filter(
            business_object=business_object,
        )

        evidence = KnowledgeEvidence.objects.filter(
            business_object=business_object,
        )

        latest_fact = facts.order_by(
            "-updated_at",
        ).first()

        latest_evidence = evidence.order_by(
            "-created_at",
        ).first()

        confidence = evidence.aggregate(
            Avg("confidence")
        )["confidence__avg"]

        return {

            "fact_count": facts.count(),

            "evidence_count": evidence.count(),

            "latest_fact": (
                latest_fact.fact_value
                if latest_fact
                else None
            ),

            "latest_evidence": (
                latest_evidence.title
                if latest_evidence
                else None
            ),

            "first_seen": (
                evidence.order_by(
                    "created_at",
                ).first().created_at
                if evidence.exists()
                else None
            ),

            "last_seen": (
                latest_evidence.created_at
                if latest_evidence
                else None
            ),

            "average_confidence": (
                round(confidence, 2)
                if confidence is not None
                else 0
            ),
        }