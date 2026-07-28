from knowledge.services.risk.base_risk_engine import (
    BaseRiskEngine,
)


class CommunicationRiskEngine(
    BaseRiskEngine,
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

            level = "low"

        elif score >= 50:

            level = "medium"

        else:

            level = "high"

        return {

            "category": self.category,

            "level": level,

            "score": score,

        }