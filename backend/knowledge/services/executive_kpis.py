from inbox.models import Organization
from context.models import (
    BusinessObject,
    Person,
)
from knowledge.models import (
    KnowledgeEvidence,
    KnowledgeFact,
)


class ExecutiveKPIService:

    def build(self, *, organization):

        return {

            "customers":
                BusinessObject.objects.filter(
                    organization=organization,
                ).count(),

            "people":
                Person.objects.filter(
                    organization=organization,
                ).count(),

            "knowledge":

                KnowledgeFact.objects.filter(
                    organization=organization,
                ).count(),

            "evidence":

                KnowledgeEvidence.objects.filter(
                    organization=organization,
                ).count(),

        }