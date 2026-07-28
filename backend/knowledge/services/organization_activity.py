"""
Enterprise Organization Activity Service
"""

from itertools import chain

from knowledge.models import (
    KnowledgeEvidence,
    KnowledgeFact,
)


class OrganizationActivityService:
    """
    Builds an organization-wide activity feed.
    """

    def build(
        self,
        *,
        organization,
        limit=100,
    ):

        evidence = []

        queryset = KnowledgeEvidence.objects.filter(
            organization=organization,
        ).select_related(
            "business_object",
        )

        for item in queryset:

            evidence.append(
                {
                    "type": "EVIDENCE",
                    "business_object": item.business_object.name,
                    "title": item.title,
                    "summary": item.summary,
                    "timestamp": item.created_at,
                }
            )

        facts = []

        queryset = KnowledgeFact.objects.filter(
            organization=organization,
        ).select_related(
            "business_object",
        )

        for item in queryset:

            facts.append(
                {
                    "type": "FACT",
                    "business_object": item.business_object.name,
                    "title": item.fact_key,
                    "summary": item.fact_value,
                    "timestamp": item.updated_at,
                }
            )

        activity = sorted(
            chain(evidence, facts),
            key=lambda x: x["timestamp"],
            reverse=True,
        )

        return activity[:limit]