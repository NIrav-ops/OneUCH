from knowledge.services.opportunity.base_opportunity_engine import (
    BaseOpportunityEngine,
)


class OrganizationOpportunityEngine(
    BaseOpportunityEngine,
):

    category = "organization"

    def build(
        self,
        *,
        organization,
    ):

        return {

            "category": self.category,

            "level": "high",

            "score": 95,

        }