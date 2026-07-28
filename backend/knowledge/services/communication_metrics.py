"""
Enterprise Communication Metrics Service
"""

from django.db.models import Count

from knowledge.models import KnowledgeEvidence


class CommunicationMetricsService:
    """
    Calculates communication metrics for a BusinessObject.
    """

    def build(
        self,
        *,
        business_object,
    ):

        queryset = KnowledgeEvidence.objects.filter(
            business_object=business_object,
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

        latest = queryset.order_by("-created_at").first()

        metrics["last_activity"] = (
            latest.created_at if latest else None
        )

        return metrics    