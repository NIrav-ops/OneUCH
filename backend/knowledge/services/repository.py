import logging

from django.db import transaction

from knowledge.models import (
    BusinessIdentity,
    KnowledgeEvidence,
    KnowledgeFact,
)

from knowledge.services.identity_normalizer import (
    IdentityNormalizer,
)

from knowledge.services.base_repository import (
    BaseRepository,
)

from knowledge.services.validators import (
    IdentityValidator,
    EvidenceValidator,
    FactValidator,
)

from knowledge.services.exceptions import (
    RepositoryError,
    EvidenceAlreadyExists,
    FactAlreadyExists,
)

from platform_core.events.publisher import (
    EventPublisher,
)

from platform_core.events.factory import (
    EventFactory,
)

from platform_core.events.names import (
    KNOWLEDGE_CREATED,
)

logger = logging.getLogger(__name__)



class IdentityRepository(BaseRepository):

    model = BusinessIdentity

    @staticmethod
    @transaction.atomic
    def create_identity(
        *,
        business_object,
        identity_type,
        value,
        source="manual",
        lifecycle="DISCOVERED",
        confidence_score=100,
        trust_score=0,
        is_primary=False,
        metadata=None,
    ):

        if metadata is None:
            metadata = {}

        normalized_value = IdentityNormalizer.normalize(
            identity_type,
            value,
        )

        identity = BusinessIdentity.objects.create(
            business_object=business_object,
            identity_type=identity_type,
            value=value,
            normalized_value=normalized_value,
            source=source,
            lifecycle=lifecycle,
            confidence_score=confidence_score,
            trust_score=trust_score,
            is_primary=is_primary,
            metadata=metadata,
        )

        return identity

    @staticmethod
    def get_identity(identity_id):

        return BusinessIdentity.objects.filter(
            id=identity_id
        ).first()

    @staticmethod
    def find_identity(
        *,
        business_object,
        identity_type,
        value,
    ):

        normalized_value = IdentityNormalizer.normalize(
            identity_type,
            value,
        )

        return BusinessIdentity.objects.filter(
            business_object=business_object,
            identity_type=identity_type,
            normalized_value=normalized_value,
        ).first()

    @staticmethod
    @transaction.atomic
    def get_or_create_identity(
        *,
        business_object,
        identity_type,
        value,
        source="manual",
        lifecycle="DISCOVERED",
        confidence_score=100,
        trust_score=0,
        is_primary=False,
        metadata=None,
    ):

        identity = IdentityRepository.find_identity(
            business_object=business_object,
            identity_type=identity_type,
            value=value,
        )

        if identity:
            return identity, False

        identity = IdentityRepository.create_identity(
            business_object=business_object,
            identity_type=identity_type,
            value=value,
            source=source,
            lifecycle=lifecycle,
            confidence_score=confidence_score,
            trust_score=trust_score,
            is_primary=is_primary,
            metadata=metadata,
        )

        return identity, True

    @staticmethod
    @transaction.atomic
    def verify_identity(identity):

        identity.lifecycle = "VERIFIED"

        identity.trust_score = 100

        identity.save(
            update_fields=[
                "lifecycle",
                "trust_score",
                "updated_at",
            ]
        )

        return identity

    @staticmethod
    @transaction.atomic
    def archive_identity(identity):

        identity.lifecycle = "ARCHIVED"

        identity.save(
            update_fields=[
                "lifecycle",
                "updated_at",
            ]
        )

        return identity

    @staticmethod
    def search(
        *,
        identity_type=None,
        value=None,
        business_object=None,
    ):

        qs = BusinessIdentity.objects.all()

        if business_object:
            qs = qs.filter(
                business_object=business_object
            )

        if identity_type:
            qs = qs.filter(
                identity_type=identity_type
            )

        if value:

            normalized = IdentityNormalizer.normalize(
                identity_type,
                value,
            )

            qs = qs.filter(
                normalized_value=normalized
            )

        return qs

# ==========================================================
# Evidence Repository
# ==========================================================


class EvidenceRepository(BaseRepository):

    """
    Enterprise repository for KnowledgeEvidence.

    Responsibilities

    - Create evidence
    - Search evidence
    - Archive evidence
    - Verify evidence
    - Duplicate detection
    - Bulk operations
    """

    model = KnowledgeEvidence

    # -----------------------------------------------------
    # Create
    # -----------------------------------------------------

    @transaction.atomic
    def create_evidence(self, **payload):

        EvidenceValidator.validate(payload)

        duplicate = self.find_duplicate(
            organization=payload["organization"],
            message=payload["message"],
            evidence_type=payload["evidence_type"],
            title=payload["title"],
        )

        if duplicate:
            raise EvidenceAlreadyExists(
                "Evidence already exists."
            )

        evidence = self.create(**payload)

        logger.info(
            "KnowledgeEvidence created (%s)",
            evidence.pk,
        )

        # --------------------------------------------
        # Publish Enterprise Domain Event
        # --------------------------------------------

        EventPublisher().publish(
            EventFactory.create(
                name=KNOWLEDGE_CREATED,
                payload={
                    "evidence_id": evidence.id,
                    "business_object": (
                        evidence.business_object.id
                        if evidence.business_object
                        else None
                    ),
                    "organization": evidence.organization.id,
                    "message_id": (
                        evidence.message.id
                        if evidence.message
                        else None
                    ),
                    "channel": evidence.source_channel,
                },
            )
        )

        return evidence

    # -----------------------------------------------------
    # Duplicate Detection
    # -----------------------------------------------------

    def find_duplicate(
        self,
        *,
        organization,
        message,
        evidence_type,
        title,
    ):

        return self.model.objects.filter(
            organization=organization,
            message=message,
            evidence_type=evidence_type,
            title=title,
            is_archived=False,
        ).first()

    # -----------------------------------------------------
    # Get
    # -----------------------------------------------------

    def get_evidence(self, evidence_id):

        return self.get(
            id=evidence_id,
        )

    # -----------------------------------------------------
    # Search
    # -----------------------------------------------------

    def search(
        self,
        *,
        organization=None,
        business_object=None,
        conversation=None,
        evidence_type=None,
        active_only=True,
    ):

        qs = self.model.objects.all()

        if organization:
            qs = qs.filter(
                organization=organization,
            )

        if business_object:
            qs = qs.filter(
                business_object=business_object,
            )

        if conversation:
            qs = qs.filter(
                conversation=conversation,
            )

        if evidence_type:
            qs = qs.filter(
                evidence_type=evidence_type,
            )

        if active_only:

            qs = qs.filter(
                is_archived=False,
                is_active=True,
            )

        return qs

    # -----------------------------------------------------
    # Verify
    # -----------------------------------------------------

    @transaction.atomic
    def verify(self, evidence):

        evidence.is_verified = True

        evidence.save(
            update_fields=[
                "is_verified",
                "updated_at",
            ]
        )

        logger.info(
            "KnowledgeEvidence verified (%s)",
            evidence.pk,
        )

        return evidence

    # -----------------------------------------------------
    # Archive
    # -----------------------------------------------------

    @transaction.atomic
    def archive(self, evidence):

        evidence.is_archived = True
        evidence.is_active = False

        evidence.save(
            update_fields=[
                "is_archived",
                "is_active",
                "updated_at",
            ]
        )

        logger.info(
            "KnowledgeEvidence archived (%s)",
            evidence.pk,
        )

        return evidence

    # -----------------------------------------------------
    # Bulk Archive
    # -----------------------------------------------------

    @transaction.atomic
    def bulk_archive(self, queryset):

        count = queryset.update(
            is_archived=True,
            is_active=False,
        )

        logger.info(
            "%s evidence archived.",
            count,
        )

        return count

    # -----------------------------------------------------
    # Business History
    # -----------------------------------------------------

    def history(
        self,
        business_object,
    ):

        return self.model.objects.filter(
            business_object=business_object,
            is_archived=False,
        ).order_by(
            "-created_at"
        )
# ==========================================================
# Fact Repository
# ==========================================================

class FactRepository(BaseRepository):
    """
    Enterprise repository for KnowledgeFact.
    """

    model = KnowledgeFact

    # -----------------------------------------------------
    # Create
    # -----------------------------------------------------

    @transaction.atomic
    def create_fact(self, **payload):

        FactValidator.validate(payload)

        duplicate = self.find_fact(
            business_object=payload["business_object"],
            fact_key=payload["fact_key"],
        )

        if duplicate:
            raise FactAlreadyExists(
                "Fact already exists."
            )

        fact = self.create(**payload)

        logger.info(
            "KnowledgeFact created (%s)",
            fact.pk,
        )

        return fact

    # -----------------------------------------------------
    # Find
    # -----------------------------------------------------

    def find_fact(
        self,
        *,
        business_object,
        fact_key,
    ):

        return self.model.objects.filter(
            business_object=business_object,
            fact_key=fact_key,
            status="ACTIVE",
        ).first()

    # -----------------------------------------------------
    # UPSERT
    # -----------------------------------------------------

    @transaction.atomic
    def upsert_fact(self, **payload):

        FactValidator.validate(payload)

        fact = self.find_fact(
            business_object=payload["business_object"],
            fact_key=payload["fact_key"],
        )

        if fact:

            changed = False

            if fact.fact_value != payload["fact_value"]:
                fact.fact_value = payload["fact_value"]
                changed = True

            if payload.get("confidence") is not None:
                if fact.confidence != payload["confidence"]:
                    fact.confidence = payload["confidence"]
                    changed = True

            if payload.get("metadata") is not None:
                fact.metadata = payload["metadata"]
                changed = True

            if payload.get("primary_evidence") is not None:
                fact.primary_evidence = payload["primary_evidence"]
                changed = True

            if payload.get("source_channel"):
                fact.source_channel = payload["source_channel"]
                changed = True

            if payload.get("fact_type"):
                fact.fact_type = payload["fact_type"]
                changed = True

            if changed:
                fact.save()

                logger.info(
                    "KnowledgeFact updated (%s)",
                    fact.pk,
                )

            return fact, False

        fact = self.create(**payload)

        logger.info(
            "KnowledgeFact created (%s)",
            fact.pk,
        )

        return fact, True

    # -----------------------------------------------------
    # Verify
    # -----------------------------------------------------

    @transaction.atomic
    def verify(self, fact):

        fact.is_verified = True
        fact.save(
            update_fields=[
                "is_verified",
                "updated_at",
            ]
        )

        return fact

    # -----------------------------------------------------
    # Archive
    # -----------------------------------------------------

    @transaction.atomic
    def archive(self, fact):

        fact.status = "INACTIVE"

        fact.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return fact

    # -----------------------------------------------------
    # Search
    # -----------------------------------------------------

    def search(
        self,
        *,
        organization=None,
        business_object=None,
        fact_key=None,
        status="ACTIVE",
    ):

        qs = self.model.objects.all()

        if organization:
            qs = qs.filter(
                organization=organization,
            )

        if business_object:
            qs = qs.filter(
                business_object=business_object,
            )

        if fact_key:
            qs = qs.filter(
                fact_key=fact_key,
            )

        if status:
            qs = qs.filter(
                status=status,
            )

        return qs

    # -----------------------------------------------------
    # Business Facts
    # -----------------------------------------------------

    def get_business_facts(
        self,
        business_object,
    ):

        return self.model.objects.filter(
            business_object=business_object,
            status="ACTIVE",
        ).order_by(
            "fact_key"
        )
# ==========================================================
# Enterprise Knowledge Repository
# ==========================================================


class KnowledgeRepository:
    """
    Enterprise Knowledge Repository

    This class acts as the single entry point into
    the Knowledge layer.

    Future integrations such as:

        Redis
        OpenSearch
        Neo4j
        Vector DB
        Audit Logs

    will be added here without changing callers.
    """

    def __init__(self):

        self.identity = IdentityRepository()

        self.evidence = EvidenceRepository()

        self.fact = FactRepository()

    # -----------------------------------------------------
    # Identity
    # -----------------------------------------------------

    def create_identity(self, **payload):

        return self.identity.create_identity(
            **payload
        )

    def get_or_create_identity(self, **payload):

        return self.identity.get_or_create_identity(
            **payload
        )

    def verify_identity(self, identity):

        return self.identity.verify_identity(
            identity
        )

    def archive_identity(self, identity):

        return self.identity.archive_identity(
            identity
        )

    # -----------------------------------------------------
    # Evidence
    # -----------------------------------------------------

    def create_evidence(self, **payload):

        return self.evidence.create_evidence(
            **payload
        )

    def verify_evidence(self, evidence):

        return self.evidence.verify(
            evidence
        )

    def archive_evidence(self, evidence):

        return self.evidence.archive(
            evidence
        )

    def search_evidence(self, **filters):

        return self.evidence.search(
            **filters
        )

    def evidence_history(
        self,
        business_object,
    ):

        return self.evidence.history(
            business_object
        )

    # -----------------------------------------------------
    # Facts
    # -----------------------------------------------------

    def create_fact(self, **payload):

        return self.fact.create_fact(
            **payload
        )

    def upsert_fact(self, **payload):

        return self.fact.upsert_fact(
            **payload
        )

    def verify_fact(self, fact):

        return self.fact.verify(
            fact
        )

    def archive_fact(self, fact):

        return self.fact.archive(
            fact
        )

    def search_facts(self, **filters):

        return self.fact.search(
            **filters
        )

    def business_facts(
        self,
        business_object,
    ):

        return self.fact.get_business_facts(
            business_object
        )