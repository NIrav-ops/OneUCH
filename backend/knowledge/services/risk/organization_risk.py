from knowledge.services.risk.base_risk_engine import (
    BaseRiskEngine,
)


class OrganizationRiskEngine(
    BaseRiskEngine,
):

    category = "organization"

    def build(
        self,
        *,
        organization,
    ):

        return {

            "category": self.category,

            "level": "low",

            "score": 92,

        }