"""
Enterprise Relationship Summary Service
"""

from context.models import BusinessRelationship


class RelationshipSummaryService:
    """
    Builds a relationship summary for a BusinessObject.
    """

    def build(
        self,
        *,
        business_object,
    ):

        outgoing = BusinessRelationship.objects.filter(
            source_object=business_object,
        ).select_related(
            "target_object",
        )

        incoming = BusinessRelationship.objects.filter(
            target_object=business_object,
        ).select_related(
            "source_object",
        )

        relationships = []

        # Outgoing
        for relation in outgoing:

            relationships.append(
                {
                    "object": relation.target_object.name,
                    "relationship": relation.relationship_type,
                    "direction": "OUTGOING",
                    "confidence": float(
                        relation.confidence
                    ),
                }
            )

        # Incoming
        for relation in incoming:

            relationships.append(
                {
                    "object": relation.source_object.name,
                    "relationship": relation.relationship_type,
                    "direction": "INCOMING",
                    "confidence": float(
                        relation.confidence
                    ),
                }
            )

        return {

            "count": len(relationships),

            "relationships": relationships,

        }