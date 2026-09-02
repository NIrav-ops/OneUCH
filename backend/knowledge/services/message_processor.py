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

from email.utils import (
    getaddresses,
)

from django.core.exceptions import (
    ValidationError,
)

from django.core.validators import (
    validate_email,
)

from email_accounts.models import (
    EmailAccount,
)

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


OUTBOUND_ADDRESS_REASON_PREFIXES = (
    "Matched email identity",
    "Matched sender domain",
    "Matched legacy domain",
)


class MessageProcessor:

    def __init__(self):

        self.repository = KnowledgeRepository()

        self.relationships = (
            RelationshipDiscoveryService()
        )


    @staticmethod
    def _normalize_email(
        value,
    ):
        email = (
            str(
                value
                or ""
            )
            .strip()
            .strip("<>")
            .lower()
        )

        if not email:
            return None

        try:
            validate_email(
                email
            )

        except ValidationError:
            return None

        return email


    @classmethod
    def _first_email(
        cls,
        value,
    ):
        source = (
            str(
                value
                or ""
            )
            .replace(
                ";",
                ",",
            )
        )

        for _, address in getaddresses(
            [
                source
            ]
        ):
            normalized = (
                cls._normalize_email(
                    address
                )
            )

            if normalized:
                return normalized

        return None


    @classmethod
    def _self_addresses(
        cls,
        message,
    ):
        addresses = set()

        user_email = cls._normalize_email(
            getattr(
                message.user,
                "email",
                "",
            )
        )

        if user_email:
            addresses.add(
                user_email
            )

        for address in (
            EmailAccount.objects
            .filter(
                user=message.user
            )
            .values_list(
                "email_address",
                flat=True,
            )
        ):
            normalized = (
                cls._normalize_email(
                    address
                )
            )

            if normalized:
                addresses.add(
                    normalized
                )

        return addresses


    @classmethod
    def _outbound_recipient_addresses(
        cls,
        message,
    ):
        self_addresses = (
            cls._self_addresses(
                message
            )
        )

        results = []
        seen = set()

        def add_address(
            value,
        ):
            normalized = (
                cls._normalize_email(
                    value
                )
            )

            if not normalized:
                return

            if normalized in self_addresses:
                return

            if normalized in seen:
                return

            seen.add(
                normalized
            )

            results.append(
                normalized
            )


        recipient_meta = (
            message.recipient_meta
            if isinstance(
                message.recipient_meta,
                dict,
            )
            else {}
        )

        structured_found = False

        for bucket in (
            "to",
            "cc",
            "bcc",
        ):
            values = (
                recipient_meta.get(
                    bucket,
                    []
                )
            )

            if not isinstance(
                values,
                list,
            ):
                continue

            for item in values:

                if not isinstance(
                    item,
                    dict,
                ):
                    continue

                value = (
                    item.get(
                        "email"
                    )
                    or
                    item.get(
                        "address"
                    )
                )

                before = len(
                    results
                )

                add_address(
                    value
                )

                if len(results) > before:
                    structured_found = True


        if not structured_found:

            source = (
                str(
                    message.recipients
                    or ""
                )
                .replace(
                    ";",
                    ",",
                )
            )

            for _, address in getaddresses(
                [
                    source
                ]
            ):
                add_address(
                    address
                )

        return results


    @staticmethod
    def _candidate_has_address_match(
        candidate,
    ):
        reasons = (
            candidate.get(
                "reasons",
                []
            )
            or []
        )

        for reason in reasons:

            for prefix in (
                OUTBOUND_ADDRESS_REASON_PREFIXES
            ):

                if str(
                    reason
                ).startswith(
                    prefix
                ):
                    return True

        return False


    def resolve_message(
        self,
        *,
        organization,
        message,
        sender="",
        subject="",
        body="",
    ):
        """
        Resolve a message without persisting Knowledge.

        Inbound:
            preserve the historical sender-first resolver.

        Outbound:
            resolve from external To/CC/BCC identities.

            If multiple distinct BusinessObjects are supported
            by recipient identities, fail closed as ambiguous
            rather than assigning the communication arbitrarily.
        """

        sender = (
            sender
            or
            message.sender
            or ""
        )

        subject = (
            subject
            or
            message.subject
            or ""
        )

        body = (
            body
            or
            message.body
            or ""
        )


        if message.direction != "outbound":

            normalized_sender = (
                self._first_email(
                    sender
                )
                or
                sender
            )

            resolution = (
                BusinessObjectResolver.resolve(
                    organization=organization,
                    sender=normalized_sender,
                    subject=subject,
                    body=body,
                )
            )

            resolution = dict(
                resolution
            )

            resolution[
                "ambiguous"
            ] = False

            resolution[
                "resolution_mode"
            ] = "sender"

            resolution[
                "resolved_address_count"
            ] = (
                1
                if normalized_sender
                else 0
            )

            return resolution


        addresses = (
            self._outbound_recipient_addresses(
                message
            )
        )


        matched_by_object = {}


        for address in addresses:

            resolution = (
                BusinessObjectResolver.resolve(
                    organization=organization,
                    sender=address,
                    subject=subject,
                    body=body,
                )
            )

            if not resolution[
                "matched"
            ]:
                continue


            for candidate in (
                resolution.get(
                    "candidates",
                    []
                )
            ):

                if not (
                    self._candidate_has_address_match(
                        candidate
                    )
                ):
                    continue

                business_object = (
                    candidate[
                        "business_object"
                    ]
                )

                existing = (
                    matched_by_object.get(
                        business_object.pk
                    )
                )

                if (
                    existing is None
                    or
                    candidate[
                        "confidence"
                    ]
                    >
                    existing[
                        "confidence"
                    ]
                ):
                    matched_by_object[
                        business_object.pk
                    ] = candidate


        if not matched_by_object:

            return {
                "matched":
                    False,

                "best_match":
                    None,

                "candidates":
                    [],

                "related_objects":
                    [],

                "ambiguous":
                    False,

                "resolution_mode":
                    "outbound_recipient",

                "resolved_address_count":
                    len(
                        addresses
                    ),
            }


        candidates = list(
            matched_by_object.values()
        )

        candidates.sort(
            key=lambda item: (
                item[
                    "confidence"
                ]
            ),
            reverse=True,
        )


        if len(
            candidates
        ) > 1:

            return {
                "matched":
                    False,

                "best_match":
                    None,

                "candidates":
                    candidates,

                "related_objects":
                    [
                        item[
                            "business_object"
                        ]
                        for item
                        in candidates
                    ],

                "ambiguous":
                    True,

                "resolution_mode":
                    "outbound_recipient_ambiguous",

                "resolved_address_count":
                    len(
                        addresses
                    ),
            }


        best_match = (
            candidates[
                0
            ]
        )


        return {
            "matched":
                True,

            "best_match":
                best_match,

            "candidates":
                [
                    best_match
                ],

            "related_objects":
                [
                    best_match[
                        "business_object"
                    ]
                ],

            "ambiguous":
                False,

            "resolution_mode":
                "outbound_recipient",

            "resolved_address_count":
                len(
                    addresses
                ),
        }


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

            resolution = (
                self.resolve_message(
                    organization=organization,
                    message=message,
                    sender=sender,
                    subject=subject,
                    body=body,
                )
            )

            if not resolution[
                "matched"
            ]:

                log_info(
                    "BusinessObject not found",
                    message_id=message.pk,
                    ambiguous=(
                        resolution.get(
                            "ambiguous",
                            False,
                        )
                    ),
                    resolution_mode=(
                        resolution.get(
                            "resolution_mode",
                            "unknown",
                        )
                    ),
                )

                return {
                    "matched":
                        False,

                    "business_object":
                        None,

                    "evidence":
                        None,

                    "fact":
                        None,

                    "relationships":
                        [],

                    "ambiguous":
                        resolution.get(
                            "ambiguous",
                            False,
                        ),

                    "resolution_mode":
                        resolution.get(
                            "resolution_mode",
                            "unknown",
                        ),
                }


            business_object = (
                resolution[
                    "best_match"
                ][
                    "business_object"
                ]
            )

            confidence = (
                resolution[
                    "best_match"
                ][
                    "confidence"
                ]
            )

            reasons = (
                resolution[
                    "best_match"
                ][
                    "reasons"
                ]
            )


            if source_channel in (
                "gmail",
                "outlook",
            ):

                evidence_type = (
                    "EMAIL"
                )

            elif source_channel == "teams":

                evidence_type = (
                    "MEETING"
                )

            elif source_channel == "slack":

                evidence_type = (
                    "TASK"
                )

            else:

                evidence_type = (
                    "GENERAL"
                )


            resolution_mode = (
                resolution.get(
                    "resolution_mode",
                    "sender",
                )
            )


            evidence = (
                self.repository.create_evidence(
                    organization=organization,
                    business_object=(
                        business_object
                    ),
                    conversation=(
                        message.conversation
                    ),
                    message=message,
                    evidence_type=(
                        evidence_type
                    ),
                    title=(
                        subject
                        or
                        "Communication"
                    ),
                    summary=(
                        body[
                            :500
                        ]
                    ),
                    resolver_reason=(
                        "\n".join(
                            reasons
                        )
                    ),
                    confidence=confidence,
                    source_channel=(
                        source_channel
                    ),
                    metadata={
                        "sender":
                            sender,

                        "direction":
                            message.direction,

                        "resolution_mode":
                            resolution_mode,

                        "resolved_address_count":
                            resolution.get(
                                "resolved_address_count",
                                0,
                            ),
                    },
                )
            )


            fact, created = (
                self.repository.upsert_fact(
                    organization=organization,
                    business_object=(
                        business_object
                    ),
                    primary_evidence=(
                        evidence
                    ),
                    fact_key=(
                        "LAST_COMMUNICATION"
                    ),
                    fact_value=(
                        subject
                        or
                        "Communication"
                    ),
                    confidence=confidence,
                    source_channel=(
                        source_channel
                    ),
                    metadata={
                        "sender":
                            sender,

                        "direction":
                            message.direction,

                        "resolution_mode":
                            resolution_mode,
                    },
                )
            )


            related_objects = (
                resolution.get(
                    "related_objects",
                    [],
                )
            )


            discovered_relationships = (
                self.relationships.discover(
                    source_object=(
                        business_object
                    ),
                    related_objects=(
                        related_objects
                    ),
                    source=(
                        source_channel
                    ),
                )
            )


            candidate_relationships = (
                self.relationships
                .discover_between_candidates(
                    business_objects=(
                        related_objects
                    ),
                    source=(
                        source_channel
                    ),
                )
            )


            discovered_relationships.extend(
                candidate_relationships
            )


            log_info(
                "Knowledge processing completed",
                message_id=message.pk,
                business_object=(
                    business_object.id
                ),
                confidence=confidence,
                resolution_mode=(
                    resolution_mode
                ),
            )


            return {
                "matched":
                    True,

                "business_object":
                    business_object,

                "evidence":
                    evidence,

                "fact":
                    fact,

                "fact_created":
                    created,

                "relationships":
                    discovered_relationships,

                "ambiguous":
                    False,

                "resolution_mode":
                    resolution_mode,
            }


        except Exception as exc:

            log_error(
                "Knowledge processing failed",
                error=str(
                    exc
                ),
                message_id=message.pk,
            )

            raise
