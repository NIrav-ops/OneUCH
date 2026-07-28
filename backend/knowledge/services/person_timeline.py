"""
Enterprise People Timeline Service
"""

from knowledge.models import (
    KnowledgeEvidence,
)


class PersonTimelineService:
    """
    Builds the chronological timeline for a Person.
    """

    def build(
        self,
        *,
        person,
    ):

        queryset = KnowledgeEvidence.objects.filter(
            person=person,
        ).order_by(
            "-created_at",
        )

        timeline = []

        for evidence in queryset:

            timeline.append(
                {
                    "title": evidence.title,
                    "summary": evidence.summary,
                    "type": evidence.evidence_type,
                    "channel": evidence.source_channel,
                    "timestamp": evidence.created_at,
                    "confidence": evidence.confidence,
                }
            )

        return timeline