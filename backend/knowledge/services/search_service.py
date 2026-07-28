"""
Enterprise Global Search Service
"""

from context.models import (
    BusinessObject,
    Person,
)

from inbox.models import Organization

from knowledge.models import (
    KnowledgeFact,
    KnowledgeEvidence,
)


class SearchService:
    """
    Global enterprise search.

    Future:

    - Semantic Search
    - Vector Search
    - AI Ranking
    - ElasticSearch
    """

    def search(
        self,
        *,
        organization,
        query,
    ):

        return {

            "business_objects": list(

                BusinessObject.objects.filter(

                    organization=organization,

                    name__icontains=query,

            ).values(

                "id",

                "name",

                "status",

            )

        ),

            "people": list(

                Person.objects.filter(

                    organization=organization,

                ).filter(

                    full_name__icontains=query,

                ).values(

                    "id",

                    "full_name",

                    "email",

                )

            ),

            "organizations": list(

                Organization.objects.filter(

                    name__icontains=query,

                ).values(

                    "id",

                    "name",

                )

            ),

            "knowledge": list(

                KnowledgeFact.objects.filter(

                    organization=organization,

                    fact_value__icontains=query,

                ).values(

                    "id",

                    "fact_key",

                    "fact_value",

                )

            ),

        }