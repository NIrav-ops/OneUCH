"""
Enterprise Activity Feed Service
"""

from itertools import chain

from knowledge.models import (
    KnowledgeEvidence,
    KnowledgeFact,
)


class ActivityFeedService:
    """
    Builds a unified chronological activity feed
    for a BusinessObject.
    """

    def build(
        self,
        *,
        business_object,
        limit=25,
    ):

        evidence = []

        for item in KnowledgeEvidence.objects.filter(
            business_object=business_object,
        ):

            evidence.append(
                {
                    "type": "EVIDENCE",
                    "title": item.title,
                    "summary": item.summary,
                    "timestamp": item.created_at,
                    "confidence": item.confidence,
                }
            )

        facts = []

        for item in KnowledgeFact.objects.filter(
            business_object=business_object,
        ):

            facts.append(
                {
                    "type": "FACT",
                    "title": item.fact_key,
                    "summary": item.fact_value,
                    "timestamp": item.updated_at,
                    "confidence": item.confidence,
                }
            )

        activity = sorted(
            chain(evidence, facts),
            key=lambda x: x["timestamp"],
            reverse=True,
        )

        return activity[:limit]