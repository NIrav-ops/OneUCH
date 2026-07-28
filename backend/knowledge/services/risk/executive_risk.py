from knowledge.services.risk.communication_risk import (
    CommunicationRiskEngine,
)

from knowledge.services.risk.knowledge_risk import (
    KnowledgeRiskEngine,
)

from knowledge.services.risk.relationship_risk import (
    RelationshipRiskEngine,
)

from knowledge.services.risk.organization_risk import (
    OrganizationRiskEngine,
)


class ExecutiveRiskService:

    def __init__(self):

        self.communication = (
            CommunicationRiskEngine()
        )

        self.knowledge = (
            KnowledgeRiskEngine()
        )

        self.relationship = (
            RelationshipRiskEngine()
        )

        self.organization = (
            OrganizationRiskEngine()
        )

    def build(
        self,
        *,
        organization,
        communication,
    ):

        communication_risk = (
            self.communication.build(
                communication=communication,
            )
        )

        knowledge_risk = (
            self.knowledge.build(
                organization=organization,
            )
        )

        relationship_risk = (
            self.relationship.build(
                organization=organization,
            )
        )

        organization_risk = (
            self.organization.build(
                organization=organization,
            )
        )

        return {

            "communication": communication_risk,

            "knowledge": knowledge_risk,

            "relationship": relationship_risk,

            "organization": organization_risk,

        }