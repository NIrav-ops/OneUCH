from knowledge.services.risk.base_risk_engine import (
    BaseRiskEngine,
)


class RelationshipRiskEngine(
    BaseRiskEngine,
):

    category = "relationship"

    def build(
        self,
        *,
        organization,
    ):

        return {

            "category": self.category,

            "level": "low",

            "score": 95,

        }