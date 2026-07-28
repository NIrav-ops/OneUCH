from knowledge.services.ai.executive_briefing import (
    ExecutiveBriefingService,
)

from knowledge.services.ai.recommendation_engine import (
    RecommendationEngine,
)

from knowledge.services.ai.priority_engine import (
    PriorityEngine,
)

from knowledge.services.ai.risk_engine import (
    AIRiskEngine,
)

from knowledge.services.ai.opportunity_engine import (
    AIOpportunityEngine,
)


class AIIntelligenceService:

    def __init__(self):

        self.briefing = (
            ExecutiveBriefingService()
        )

        self.recommendations = (
            RecommendationEngine()
        )

        self.priority = (
            PriorityEngine()
        )

        self.risk = (
            AIRiskEngine()
        )

        self.opportunity = (
            AIOpportunityEngine()
        )

    def build(
        self,
        *,
        organization,
        executive_dashboard,
    ):

        return {

            "briefing":

                self.briefing.build(
                    executive_dashboard=executive_dashboard,
                ),

            "recommendations":

                self.recommendations.build(
                    organization=organization,
                ),

            "risk":

                self.risk.build(
                    organization=organization,
                ),

            "opportunity":

                self.opportunity.build(
                    organization=organization,
                ),

        }