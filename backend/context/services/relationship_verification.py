from django.utils import timezone
from datetime import timedelta
import logging

from context.models import BusinessRelationship

logger = logging.getLogger(__name__)


class RelationshipVerificationService:
    """
    Enterprise relationship verification service.
    """

    STALE_AFTER_DAYS = 90

    @classmethod
    def verify(cls, relationship):
        """
        Mark a relationship as verified.
        """

        relationship.last_verified = timezone.now()

        relationship.save(
            update_fields=[
                "last_verified",
                "updated_at",
            ]
        )

        logger.info(
            "Relationship verified",
            extra={
                "relationship": relationship.id,
            },
        )

        return relationship

    @classmethod
    def is_stale(cls, relationship):
        """
        Determine whether a relationship is stale.
        """

        if relationship.last_verified is None:
            return True

        return relationship.last_verified < (
            timezone.now() - timedelta(days=cls.STALE_AFTER_DAYS)
        )

    @classmethod
    def stale_relationships(cls):
        """
        Return all stale relationships.
        """

        cutoff = timezone.now() - timedelta(days=cls.STALE_AFTER_DAYS)

        return BusinessRelationship.objects.filter(
            last_verified__lt=cutoff
        )