"""
Enterprise Timeline Builder

Builds a chronological timeline for a BusinessObject.

Future sources:

- Emails
- Meetings
- Actions
- Approvals
- Documents
- Tasks
- AI Events
"""

from knowledge.models import KnowledgeEvidence


class TimelineService:

    def build(
        self,
        *,
        business_object,
        limit=50,
    ):

        evidence = (

            KnowledgeEvidence.objects

            .filter(
                business_object=business_object,
            )

            .order_by(
                "-created_at",
            )[:limit]

        )

        timeline = []

        for item in evidence:

            timeline.append(
                {
                    "id": item.id,
                    "type": item.evidence_type,
                    "title": item.title,
                    "summary": item.summary,
                    "confidence": item.confidence,
                    "created_at": item.created_at,
                    "source_channel": item.source_channel,
                }
            )

        return timeline