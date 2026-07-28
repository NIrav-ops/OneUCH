from knowledge.models import (
    KnowledgeEvidence,
)


class ExecutiveActivityService:

    def build(
        self,
        *,
        organization,
        limit=20,
    ):

        queryset = (

            KnowledgeEvidence.objects.filter(

                organization=organization,

            )

            .order_by("-created_at")[:limit]

        )

        activity = []

        for evidence in queryset:

            activity.append(

                {

                    "title": evidence.title,

                    "type": evidence.evidence_type,

                    "channel": evidence.source_channel,

                    "created_at": evidence.created_at,

                }

            )

        return activity