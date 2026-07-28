from knowledge.services.opportunity.base_opportunity_engine import (
    BaseOpportunityEngine,
)


class RelationshipOpportunityEngine(
    BaseOpportunityEngine,
):

    category = "relationship"

    def build(
        self,
        *,
        organization,
    ):

        return {

            "category": self.category,

            "level": "high",

            "score": 92,

        }