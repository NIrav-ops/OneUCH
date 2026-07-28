import logging
from typing import List
from context.models import BusinessRelationship
from context.services.relationship_repository import (
    RelationshipRepository,
)

logger = logging.getLogger(__name__)


class RelationshipDiscoveryService:
    """
    Enterprise Relationship Discovery Service.

    Responsible for discovering relationships between
    Business Objects from communication events.

    Current Version:
        Rule-based

    Future Versions:
        - AI
        - NLP
        - LLM
        - Graph Learning
    """

    def __init__(self):

        self.repository = RelationshipRepository()

    def discover(
        self,
        *,
        source_object,
        related_objects,
        relationship_type="RELATED_TO",
        source="resolver",
    ) -> List[BusinessRelationship]:
        """
        Discover relationships between BusinessObjects.

        Creates or strengthens relationships between the
        source object and every related object.
        """

        discovered = []

        if source_object is None:
            return discovered

        # Remove duplicates while preserving order
        unique_objects = []

        for obj in related_objects:

            if obj is None:
                continue

            if obj == source_object:
                continue

            if obj not in unique_objects:
                unique_objects.append(obj)

        for target_object in unique_objects:

            try:

                relationship, created = (
                    self.repository.get_or_create_relationship(
                        source_object=source_object,
                        target_object=target_object,
                        relationship_type=relationship_type,
                        source=source,
                    )
                )

                if created:

                    metadata = relationship.metadata or {}

                    metadata["first_source"] = source

                    relationship.metadata = metadata

                    relationship.save(
                        update_fields=[
                            "metadata",
                        ]
                    )

                else:

                    relationship = (
                        self.repository.strengthen_relationship(
                            relationship
                        )
                    )

                    metadata = relationship.metadata or {}

                    metadata["last_source"] = source

                    relationship.metadata = metadata

                    relationship.save(
                        update_fields=[
                            "metadata",
                        ]
                    )

                discovered.append(relationship)

            except Exception:

                logger.exception(
                    "Relationship discovery failed",
                    extra={
                        "source_object": getattr(source_object, "id", None),
                        "target_object": getattr(target_object, "id", None),
                    },
                )

        return discovered
    
    def discover_between_candidates(
        self,
        *,
        business_objects,
        relationship_type="RELATED_TO",
        source="resolver",
    ) -> List[BusinessRelationship]:
        """
        Discover relationships between every pair of
        BusinessObjects.

        Example:

        Google

        Microsoft

        Infosys

        creates

        Google ↔ Microsoft

        Google ↔ Infosys

        Microsoft ↔ Infosys
        """

        discovered = []

        objects = []

        for obj in business_objects:

            if obj and obj not in objects:
                objects.append(obj)

        total = len(objects)

        for i in range(total):

            for j in range(i + 1, total):

                try:

                    relationship, created = (
                        self.repository.get_or_create_relationship(
                            source_object=objects[i],
                            target_object=objects[j],
                            relationship_type=relationship_type,
                            source=source,
                        )
                    )

                    if not created:

                        relationship = (
                            self.repository.strengthen_relationship(
                                relationship
                            )
                        )

                    discovered.append(
                        relationship
                    )

                except Exception:

                    logger.exception(
                        "Candidate relationship discovery failed",
                        extra={
                            "source_object": objects[i].id,
                            "target_object": objects[j].id,
                        },
                    )

                if not created:

                    relationship = (
                        self.repository.strengthen_relationship(
                            relationship
                        )
                    )

                discovered.append(
                    relationship
                )

        return discovered