from knowledge.services.opportunity.base_opportunity_engine import (
    BaseOpportunityEngine,
)


class KnowledgeOpportunityEngine(
    BaseOpportunityEngine,
):

    category = "knowledge"

    def build(
        self,
        *,
        organization,
    ):

        return {

            "category": self.category,

            "level": "high",

            "score": 90,

        }