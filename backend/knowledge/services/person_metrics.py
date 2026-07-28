"""
Enterprise Person Metrics Service
"""

from knowledge.models import (
    KnowledgeEvidence,
)


class PersonMetricsService:
    """
    Calculates communication metrics for a Person.
    """

    def build(
        self,
        *,
        person,
    ):

        queryset = KnowledgeEvidence.objects.filter(
            person=person,
        )

        metrics = {

            "total_evidence": queryset.count(),

            "emails": queryset.filter(
                evidence_type="EMAIL",
            ).count(),

            "meetings": queryset.filter(
                evidence_type="MEETING",
            ).count(),

            "tasks": queryset.filter(
                evidence_type="TASK",
            ).count(),

            "documents": queryset.filter(
                evidence_type="DOCUMENT",
            ).count(),

            "approvals": queryset.filter(
                evidence_type="APPROVAL",
            ).count(),

        }

        latest = queryset.order_by(
            "-created_at"
        ).first()

        metrics["last_activity"] = (

            latest.created_at

            if latest

            else None

        )

        return metrics