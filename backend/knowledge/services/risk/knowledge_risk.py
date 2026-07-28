from knowledge.services.risk.base_risk_engine import (
    BaseRiskEngine,
)


class KnowledgeRiskEngine(
    BaseRiskEngine,
):

    category = "knowledge"

    def build(
        self,
        *,
        organization,
    ):

        return {

            "category": self.category,

            "level": "low",

            "score": 90,

        }