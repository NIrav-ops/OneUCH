"""
Enterprise Organization Metrics Service
"""

from context.models import (
    BusinessObject,
    BusinessRelationship,
)

from knowledge.models import (
    KnowledgeEvidence,
    KnowledgeFact,
)


class OrganizationMetricsService:
    """
    Calculates organization-wide knowledge metrics.
    """

    def build(
        self,
        *,
        organization,
    ):

        return {

            "business_objects": BusinessObject.objects.filter(
                organization=organization,
            ).count(),

            "relationships": BusinessRelationship.objects.filter(
                source_object__organization=organization,
            ).count(),

            "knowledge_facts": KnowledgeFact.objects.filter(
                organization=organization,
            ).count(),

            "knowledge_evidence": KnowledgeEvidence.objects.filter(
                organization=organization,
            ).count(),

        }