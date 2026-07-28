from knowledge.services.opportunity.communication_opportunity import (
    CommunicationOpportunityEngine,
)

from knowledge.services.opportunity.knowledge_opportunity import (
    KnowledgeOpportunityEngine,
)

from knowledge.services.opportunity.relationship_opportunity import (
    RelationshipOpportunityEngine,
)

from knowledge.services.opportunity.organization_opportunity import (
    OrganizationOpportunityEngine,
)


class ExecutiveOpportunityService:

    def __init__(self):

        self.communication = (
            CommunicationOpportunityEngine()
        )

        self.knowledge = (
            KnowledgeOpportunityEngine()
        )

        self.relationship = (
            RelationshipOpportunityEngine()
        )

        self.organization = (
            OrganizationOpportunityEngine()
        )

    def build(
        self,
        *,
        organization,
        communication,
    ):

        communication_opportunity = (
            self.communication.build(
                communication=communication,
            )
        )

        knowledge_opportunity = (
            self.knowledge.build(
                organization=organization,
            )
        )

        relationship_opportunity = (
            self.relationship.build(
                organization=organization,
            )
        )

        organization_opportunity = (
            self.organization.build(
                organization=organization,
            )
        )

        return {

            "communication": communication_opportunity,

            "knowledge": knowledge_opportunity,

            "relationship": relationship_opportunity,

            "organization": organization_opportunity,

        }