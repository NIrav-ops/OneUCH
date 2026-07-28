"""
Enterprise Executive Dashboard
"""

from knowledge.services.executive_kpis import ExecutiveKPIService
from knowledge.services.executive_activity import ExecutiveActivityService
from knowledge.services.executive_alerts import ExecutiveAlertsService
from knowledge.services.executive_risks import ExecutiveRiskService
from knowledge.services.executive_opportunities import (
    ExecutiveOpportunityService,
)

from knowledge.services.communication_intelligence import (
    CommunicationIntelligenceService,
)


class ExecutiveDashboardService:

    def __init__(self):

        self.kpis = ExecutiveKPIService()

        self.activity = ExecutiveActivityService()

        self.alerts = ExecutiveAlertsService()

        self.risks = ExecutiveRiskService()

        self.opportunities = (
            ExecutiveOpportunityService()
        )

        self.communication = (
            CommunicationIntelligenceService()
        )

    def build(
        self,
        *,
        organization,
    ):

        return {

            "kpis":
                self.kpis.build(
                    organization=organization,
                ),

            "activity":
                self.activity.build(
                    organization=organization,
                ),

            "alerts":
                self.alerts.build(),

            "risks":
                self.risks.build(),

            "opportunities":
                self.opportunities.build(),

            "communication":
                self.communication.build(
                    organization=organization,
                ),

        }