import logging
from django.db import IntegrityError
from typing import Tuple

logger = logging.getLogger(__name__)
from django.db import transaction
from django.utils import timezone
from context.models import BusinessRelationship
from context.services.relationship_confidence import (RelationshipConfidenceEngine,)
from context.services.relationship_verification import (RelationshipVerificationService,)
from context.constants import DEFAULT_RELATIONSHIP_TYPE
from context.constants import (DEFAULT_RELATIONSHIP_DIRECTION,)
from context.exceptions import (RelationshipError,)

class RelationshipRepository:

    @staticmethod
    @transaction.atomic
    def create_relationship(
        *,
        source_object,
        target_object,
        relationship_type=DEFAULT_RELATIONSHIP_TYPE,
        direction=DEFAULT_RELATIONSHIP_DIRECTION,
        confidence=100,
        evidence_count=1,
        source="resolver",
        metadata=None,
    ):
        """
        Create a new relationship.
        """

        metadata = metadata or {}

        if source_object == target_object:
            raise RelationshipError(
                "Source and Target BusinessObject cannot be identical."
            )

        try:

            relationship = BusinessRelationship.objects.create(

                source_object=source_object,
                target_object=target_object,
                relationship_type=relationship_type,
                direction=direction,
                confidence=confidence,
                evidence_count=evidence_count,
                source=source,
                metadata=metadata,
            )

            logger.info(

                "Relationship created",

                    extra={

                        "source": source_object.id,

                        "target": target_object.id,

                        "relationship_type": relationship_type,

                    },

                )

            return relationship

        except IntegrityError:

            logger.exception("Relationship creation failed")

            raise

    @staticmethod
    def get_relationship(relationship_id):
        """
        Return a relationship by ID.
        """

        return BusinessRelationship.objects.filter(
            id=relationship_id
        ).first()

    @staticmethod
    def all():
        """
        Return all relationships.
        """

        return BusinessRelationship.objects.all()
    
    @staticmethod
    def find_relationship(
        *,
        source_object,
        target_object,
        relationship_type=DEFAULT_RELATIONSHIP_TYPE,
    ):
        """
        Find an existing relationship.
        """

        return BusinessRelationship.objects.filter(
            source_object=source_object,
            target_object=target_object,
            relationship_type=relationship_type,
        ).first()
    
    @staticmethod
    @transaction.atomic
    def get_or_create_relationship(
        *,
        source_object,
        target_object,
        relationship_type=DEFAULT_RELATIONSHIP_TYPE,
        direction=DEFAULT_RELATIONSHIP_DIRECTION,
        confidence=100,
        source="resolver",
        metadata=None,
    ) -> Tuple[BusinessRelationship, bool]:

        relationship = RelationshipRepository.find_relationship(
            source_object=source_object,
            target_object=target_object,
            relationship_type=relationship_type,
        )

        if relationship:

            RelationshipRepository.strengthen_relationship(
                relationship,
                confidence_increment=1,
            )

            return relationship, False

        relationship = RelationshipRepository.create_relationship(
            source_object=source_object,
            target_object=target_object,
            relationship_type=relationship_type,
            direction=direction,
            confidence=confidence,
            source=source,
            metadata=metadata,
        )

        return relationship, True
    
    @staticmethod
    @transaction.atomic
    def strengthen_relationship(
        relationship,
        confidence_increment=1,
    ):
        """
        Strengthen an existing relationship.
        """

        relationship.evidence_count += 1

        RelationshipConfidenceEngine.update(
            relationship=relationship,
        )

        RelationshipVerificationService.verify(
            relationship
        )

        relationship.save(
            update_fields=[
                "confidence",
                "evidence_count",
                "updated_at",
                "last_verified",
            ]
        )

        return relationship
    @staticmethod
    @transaction.atomic
    def archive_relationship(
        relationship,
    ):
        """
        Soft archive relationship.
        """

        metadata = relationship.metadata or {}

        metadata["archived"] = True

        relationship.metadata = metadata

        relationship.save(
            update_fields=[
                "metadata",
                "updated_at",
            ]
        )

        return relationship

    @staticmethod
    def get_outgoing_relationships(
        business_object,
    ):
        """
        Return all outgoing relationships.
        """

        return (
            BusinessRelationship.objects
            .filter(
                source_object=business_object,
            )
            .select_related(
                "source_object",
                "target_object",
            )
            .order_by(
                "-confidence",
            )
        )
    
    @staticmethod
    def get_incoming_relationships(
        business_object,
    ):
        """
        Return all incoming relationships.
        """

        return (
            BusinessRelationship.objects
            .filter(
                target_object=business_object,
            )
            .select_related(
                "source_object",
                "target_object",
            )
            .order_by(
                "-confidence",
            )
        )
    
    @staticmethod
    def relationship_exists(
        source_object,
        target_object,
        relationship_type=DEFAULT_RELATIONSHIP_TYPE,
    ):
        """
        Check whether relationship exists.
        """

        return (
            BusinessRelationship.objects.filter(
                source_object=source_object,
                target_object=target_object,
                relationship_type=relationship_type,
            ).exists()
        )
    
    @staticmethod
    @transaction.atomic
    def delete_relationship(
        relationship,
    ):
        """
        Permanently delete relationship.
        """

        relationship.delete()

        return True