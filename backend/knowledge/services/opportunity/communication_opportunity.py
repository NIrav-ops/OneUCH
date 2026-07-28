from knowledge.services.opportunity.base_opportunity_engine import (
    BaseOpportunityEngine,
)


class CommunicationOpportunityEngine(
    BaseOpportunityEngine,
):

    category = "communication"

    def build(
        self,
        *,
        communication,
    ):

        health = communication.get(
            "health",
            {},
        )

        score = health.get(
            "score",
            0,
        )

        if score >= 80:
            level = "high"
        elif score >= 50:
            level = "medium"
        else:
            level = "low"

        return {

            "category": self.category,

            "level": level,

            "score": score,

        }