"""
Enterprise Message Processor

Single entry point for processing communications.

Responsibilities
----------------
1. Resolve Business Object
2. Store Knowledge Evidence
3. Maintain Knowledge Facts
4. Discover Relationships
5. (Future) Action Extraction
6. (Future) Approval Extraction
7. (Future) Timeline
"""

from knowledge.services.logger import (
    log_info,
    log_error,
)

from knowledge.services.repository import (
    KnowledgeRepository,
)

from knowledge.services.resolver import (
    BusinessObjectResolver,
)

from context.services.relationship_discovery import (
    RelationshipDiscoveryService,
)


class MessageProcessor:

    def __init__(self):

        self.repository = KnowledgeRepository()

        self.relationships = (
            RelationshipDiscoveryService()
        )

    def process_message(
        self,
        *,
        organization,
        message,
        sender="",
        subject="",
        body="",
        source_channel="gmail",
    ):

        try:

            log_info(
                "Processing InboxMessage",
                message_id=message.pk,
                organization=organization.id,
                platform=source_channel,
            )

            resolution = BusinessObjectResolver.resolve(
                organization=organization,
                sender=sender,
                subject=subject,
                body=body,
            )

            if not resolution["matched"]:

                log_info(
                    "BusinessObject not found",
                    message_id=message.pk,
                )

                return {
                    "matched": False,
                    "business_object": None,
                    "evidence": None,
                    "fact": None,
                    "relationships": [],
                }

            business_object = (
                resolution["best_match"]["business_object"]
            )

            confidence = (
                resolution["best_match"]["confidence"]
            )

            reasons = (
                resolution["best_match"]["reasons"]
            )

            # ---------------------------------------
            # Evidence Type
            # ---------------------------------------

            if source_channel in ("gmail", "outlook"):

                evidence_type = "EMAIL"

            elif source_channel == "teams":

                evidence_type = "MEETING"

            elif source_channel == "slack":

                evidence_type = "TASK"

            else:

                evidence_type = "GENERAL"

            # ---------------------------------------
            # Knowledge Evidence
            # ---------------------------------------

            evidence = self.repository.create_evidence(
                organization=organization,
                business_object=business_object,
                conversation=message.conversation,
                message=message,
                evidence_type=evidence_type,
                title=subject or "Communication",
                summary=body[:500],
                resolver_reason="\n".join(reasons),
                confidence=confidence,
                source_channel=source_channel,
                metadata={
                    "sender": sender,
                },
            )

            # ---------------------------------------
            # Knowledge Facts
            # ---------------------------------------

            fact, created = self.repository.upsert_fact(
                organization=organization,
                business_object=business_object,
                primary_evidence=evidence,
                fact_key="LAST_COMMUNICATION",
                fact_value=subject or "Communication",
                confidence=confidence,
                source_channel=source_channel,
                metadata={
                    "sender": sender,
                },
            )

            # ---------------------------------------
            # Relationship Discovery
            # ---------------------------------------

            related_objects = resolution.get(
                "related_objects",
                [],
            )

            discovered_relationships = (
                self.relationships.discover(
                    source_object=business_object,
                    related_objects=related_objects,
                    source=source_channel,
                )
            )

            candidate_relationships = (
                self.relationships.discover_between_candidates(
                    business_objects=related_objects,
                    source=source_channel,
                )
            )

            discovered_relationships.extend(
                candidate_relationships
            )

            log_info(
                "Knowledge processing completed",
                message_id=message.pk,
                business_object=business_object.id,
                confidence=confidence,
            )

            return {
                "matched": True,
                "business_object": business_object,
                "evidence": evidence,
                "fact": fact,
                "fact_created": created,
                "relationships": discovered_relationships,
            }

        except Exception as exc:

            log_error(
                "Knowledge processing failed",
                error=str(exc),
                message_id=message.pk,
            )

            raise