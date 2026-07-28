"""
Enterprise Executive Summary Service
"""


class ExecutiveSummaryService:
    """
    Builds an executive-friendly summary from
    Customer360 data.

    Current:
        Rule-based

    Future:
        LLM
        AI Agent
        Risk Detection
        Opportunity Detection
    """

    def build(
        self,
        *,
        business_object,
        knowledge,
        metrics,
        relationships,
    ):

        fact_count = knowledge.get(
            "fact_count",
            0,
        )

        evidence_count = knowledge.get(
            "evidence_count",
            0,
        )

        relationship_count = relationships.get(
            "count",
            0,
        )

        confidence = knowledge.get(
            "average_confidence",
            0,
        )

        if fact_count > 0:

            status = "Known Business Entity"

        else:

            status = "New Business Entity"

        headline = (
            f"{business_object.name} has "
            f"{evidence_count} communications, "
            f"{relationship_count} relationships "
            f"and {fact_count} verified knowledge facts."
        )

        return {

            "status": status,

            "headline": headline,

            "confidence": confidence,

            "last_activity": metrics.get(
                "last_activity",
            ),
        }