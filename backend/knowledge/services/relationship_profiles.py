from dataclasses import (
    asdict,
    dataclass,
)
from email.utils import (
    getaddresses,
    parseaddr,
)
from typing import Optional


from context.models import (
    Person,
)

from inbox.models import (
    InboxMessage,
    OrganizationUser,
)

from knowledge.services.commitment_ledger import (
    CommitmentLedgerService,
)

from knowledge.services.decisions import (
    DecisionsService,
)

from knowledge.services.waiting_for import (
    WaitingForService,
)


@dataclass(frozen=True)
class RelationshipProfileSummary:
    """
    One external communication relationship.

    Email is the deterministic identity key.

    Person is optional enrichment only. Relationship Profile
    therefore remains useful even when legacy Person/People360
    association has not been populated.
    """

    relationship_id: str

    organization_id: int

    person_id: Optional[int]

    email: str
    full_name: str
    company: str
    job_title: str
    domain: str

    communication_total: int
    inbound_count: int
    outbound_count: int

    last_interaction_at: object
    last_conversation_id: Optional[int]

    pending_commitments: int
    we_owe_them_pending: int
    they_owe_us_pending: int

    active_waits: int

    decisions: int
    approved_decisions: int
    rejected_decisions: int

    open_url: Optional[str]

    def to_dict(self):
        return asdict(
            self
        )


class RelationshipProfilesService:
    """
    Read-only external Relationship Profile projection.

    No new persisted relationship state is introduced.

    Authoritative sources:

        Person
            optional identity enrichment

        InboxMessage
            communication history

        CommitmentLedgerService
            accountability history

        WaitingForService
            current external obligations

        DecisionsService
            recorded approval decisions requested by
            the external relationship

    Internal organization users are excluded from this
    MVP relationship directory.
    """

    RECENT_COMMUNICATION_LIMIT = 6

    @classmethod
    def build_index(
        cls,
        *,
        organization,
    ):
        state = cls._build_state(
            organization=organization
        )

        profiles = [
            cls._build_summary(
                email=email,
                state=state,
            )
            for email in state[
                "candidate_emails"
            ]
        ]

        profiles = sorted(
            profiles,
            key=cls._profile_sort_key,
        )

        return {
            "organization_id":
                organization.id,

            "summary":
                cls._index_summary(
                    profiles
                ),

            "profiles": [
                profile.to_dict()
                for profile in profiles
            ],
        }

    @classmethod
    def build_profile(
        cls,
        *,
        organization,
        email,
    ):
        normalized = cls._normalize_email(
            email
        )

        if not normalized:
            return None

        state = cls._build_state(
            organization=organization
        )

        if (
            normalized
            not in state[
                "candidate_emails"
            ]
        ):
            return None

        profile = cls._build_summary(
            email=normalized,
            state=state,
        )

        communications = (
            state[
                "messages_by_email"
            ].get(
                normalized,
                [],
            )
        )

        commitments = (
            state[
                "commitments_by_email"
            ].get(
                normalized,
                [],
            )
        )

        waiting = (
            state[
                "waiting_by_email"
            ].get(
                normalized,
                [],
            )
        )

        decisions = (
            state[
                "decisions_by_email"
            ].get(
                normalized,
                [],
            )
        )

        return {
            "organization_id":
                organization.id,

            "profile":
                profile.to_dict(),

            "recent_communications": [
                cls._communication_dict(
                    message
                )
                for message
                in communications[
                    :cls.RECENT_COMMUNICATION_LIMIT
                ]
            ],

            "commitments": [
                item.to_dict()
                for item in commitments
            ],

            "waiting_for": [
                item.to_dict()
                for item in waiting
            ],

            "decisions": [
                item.to_dict()
                for item in decisions
            ],
        }

    # ========================================================
    # STATE
    # ========================================================

    @classmethod
    def _build_state(
        cls,
        *,
        organization,
    ):
        people = list(
            Person.objects
            .filter(
                organization=organization
            )
            .order_by(
                "id"
            )
        )

        people_by_email = {}

        internal_emails = set()

        for membership in (
            OrganizationUser.objects
            .select_related(
                "user"
            )
            .filter(
                organization=organization
            )
        ):
            email = cls._normalize_email(
                membership.user.email
            )

            if email:
                internal_emails.add(
                    email
                )

        for person in people:
            email = cls._normalize_email(
                person.email
            )

            if not email:
                continue

            people_by_email.setdefault(
                email,
                person,
            )

            if person.is_internal:
                internal_emails.add(
                    email
                )

        candidate_emails = set()

        for email, person in (
            people_by_email.items()
        ):
            if (
                email
                not in internal_emails
                and not person.is_internal
            ):
                candidate_emails.add(
                    email
                )

        messages_by_email = {}

        messages = list(
            InboxMessage.objects
            .filter(
                organization=organization,
                is_draft=False,
            )
            .select_related(
                "conversation"
            )
            .order_by(
                "-received_at",
                "-id",
            )
        )

        for message in messages:
            emails = (
                cls._message_external_emails(
                    message=message,
                    internal_emails=(
                        internal_emails
                    ),
                )
            )

            for email in emails:
                candidate_emails.add(
                    email
                )

                messages_by_email.setdefault(
                    email,
                    [],
                ).append(
                    message
                )

        commitments_by_email = {}

        commitments = (
            CommitmentLedgerService
            .build(
                organization=organization
            )
        )

        for item in commitments:
            email = cls._normalize_email(
                item.counterparty
            )

            if (
                not email
                or email
                in internal_emails
            ):
                continue

            candidate_emails.add(
                email
            )

            commitments_by_email.setdefault(
                email,
                [],
            ).append(
                item
            )

        waiting_by_email = {}

        waiting_items = (
            WaitingForService
            .build(
                organization=organization
            )
        )

        for item in waiting_items:
            email = cls._normalize_email(
                item.counterparty
            )

            if (
                not email
                or email
                in internal_emails
            ):
                continue

            candidate_emails.add(
                email
            )

            waiting_by_email.setdefault(
                email,
                [],
            ).append(
                item
            )

        decisions_by_email = {}

        decisions = (
            DecisionsService
            .build(
                organization=organization
            )
        )

        for item in decisions:
            email = cls._normalize_email(
                item.requested_by
            )

            if (
                not email
                or email
                in internal_emails
            ):
                continue

            candidate_emails.add(
                email
            )

            decisions_by_email.setdefault(
                email,
                [],
            ).append(
                item
            )

        return {
            "organization":
                organization,

            "people_by_email":
                people_by_email,

            "internal_emails":
                internal_emails,

            "candidate_emails":
                candidate_emails,

            "messages_by_email":
                messages_by_email,

            "commitments_by_email":
                commitments_by_email,

            "waiting_by_email":
                waiting_by_email,

            "decisions_by_email":
                decisions_by_email,
        }

    # ========================================================
    # PROFILE
    # ========================================================

    @classmethod
    def _build_summary(
        cls,
        *,
        email,
        state,
    ):
        person = (
            state[
                "people_by_email"
            ].get(
                email
            )
        )

        messages = (
            state[
                "messages_by_email"
            ].get(
                email,
                [],
            )
        )

        commitments = (
            state[
                "commitments_by_email"
            ].get(
                email,
                [],
            )
        )

        waiting = (
            state[
                "waiting_by_email"
            ].get(
                email,
                [],
            )
        )

        decisions = (
            state[
                "decisions_by_email"
            ].get(
                email,
                [],
            )
        )

        inbound_count = sum(
            1
            for message in messages
            if (
                message.direction
                == "inbound"
            )
        )

        outbound_count = sum(
            1
            for message in messages
            if (
                message.direction
                == "outbound"
            )
        )

        pending = [
            item
            for item in commitments
            if (
                item.status
                ==
                CommitmentLedgerService
                .STATUS_PENDING
            )
        ]

        we_owe = sum(
            1
            for item in pending
            if (
                item.direction
                ==
                CommitmentLedgerService
                .DIRECTION_WE_OWE_THEM
            )
        )

        they_owe = sum(
            1
            for item in pending
            if (
                item.direction
                ==
                CommitmentLedgerService
                .DIRECTION_THEY_OWE_US
            )
        )

        approved = sum(
            1
            for item in decisions
            if (
                item.outcome
                ==
                DecisionsService
                .OUTCOME_APPROVED
            )
        )

        rejected = sum(
            1
            for item in decisions
            if (
                item.outcome
                ==
                DecisionsService
                .OUTCOME_REJECTED
            )
        )

        latest = (
            messages[0]
            if messages
            else None
        )

        conversation_id = (
            latest.conversation_id
            if latest is not None
            else cls._fallback_conversation_id(
                commitments=commitments,
                waiting=waiting,
                decisions=decisions,
            )
        )

        return RelationshipProfileSummary(
            relationship_id=(
                f"email:{email}"
            ),

            organization_id=(
                state[
                    "organization"
                ].id
            ),

            person_id=(
                person.id
                if person
                else None
            ),

            email=email,

            full_name=(
                person.full_name
                if person
                else ""
            ),

            company=(
                person.company
                if person
                else ""
            ),

            job_title=(
                person.job_title
                if person
                else ""
            ),

            domain=(
                cls._email_domain(
                    email
                )
            ),

            communication_total=(
                len(
                    messages
                )
            ),

            inbound_count=(
                inbound_count
            ),

            outbound_count=(
                outbound_count
            ),

            last_interaction_at=(
                latest.received_at
                if latest
                else None
            ),

            last_conversation_id=(
                conversation_id
            ),

            pending_commitments=(
                len(
                    pending
                )
            ),

            we_owe_them_pending=(
                we_owe
            ),

            they_owe_us_pending=(
                they_owe
            ),

            active_waits=(
                len(
                    waiting
                )
            ),

            decisions=(
                len(
                    decisions
                )
            ),

            approved_decisions=(
                approved
            ),

            rejected_decisions=(
                rejected
            ),

            open_url=(
                cls._open_url(
                    conversation_id
                )
            ),
        )

    @staticmethod
    def _fallback_conversation_id(
        *,
        commitments,
        waiting,
        decisions,
    ):
        for collection in (
            waiting,
            commitments,
            decisions,
        ):
            for item in collection:
                conversation_id = (
                    getattr(
                        item,
                        "conversation_id",
                        None,
                    )
                )

                if conversation_id:
                    return conversation_id

        return None

    # ========================================================
    # MESSAGE IDENTITY
    # ========================================================

    @classmethod
    def _message_external_emails(
        cls,
        *,
        message,
        internal_emails,
    ):
        emails = []

        if message.direction == "inbound":
            sender = cls._normalize_email(
                message.sender
            )

            if (
                sender
                and sender
                not in internal_emails
            ):
                emails.append(
                    sender
                )

            return emails

        if message.direction == "outbound":
            for email in (
                cls._recipient_emails(
                    message.recipients
                )
            ):
                if (
                    email
                    and email
                    not in internal_emails
                    and email
                    not in emails
                ):
                    emails.append(
                        email
                    )

        return emails

    @classmethod
    def _recipient_emails(
        cls,
        value,
    ):
        normalized_value = (
            str(
                value or ""
            )
            .replace(
                ";",
                ",",
            )
        )

        emails = []

        for _name, email in getaddresses(
            [
                normalized_value
            ]
        ):
            normalized = cls._normalize_email(
                email
            )

            if (
                normalized
                and normalized
                not in emails
            ):
                emails.append(
                    normalized
                )

        return emails

    @staticmethod
    def _normalize_email(
        value,
    ):
        _name, email = parseaddr(
            str(
                value or ""
            )
        )

        normalized = (
            email
            .strip()
            .lower()
        )

        return (
            normalized
            or None
        )

    @staticmethod
    def _email_domain(
        email,
    ):
        if (
            not email
            or "@"
            not in email
        ):
            return ""

        return (
            email
            .rsplit(
                "@",
                1,
            )[1]
            .lower()
        )

    # ========================================================
    # SERIALIZATION / SUMMARY
    # ========================================================

    @classmethod
    def _communication_dict(
        cls,
        message,
    ):
        return {
            "message_id":
                message.id,

            "conversation_id":
                message.conversation_id,

            "direction":
                message.direction,

            "platform":
                message.platform,

            "subject":
                message.subject
                or "",

            "received_at":
                message.received_at,

            "open_url":
                cls._open_url(
                    message.conversation_id
                ),
        }

    @staticmethod
    def _open_url(
        conversation_id,
    ):
        if conversation_id is None:
            return None

        return (
            "/inbox?conversation="
            f"{conversation_id}"
        )

    @staticmethod
    def _profile_sort_key(
        profile,
    ):
        timestamp = (
            profile
            .last_interaction_at
            .timestamp()
            if (
                profile
                .last_interaction_at
                is not None
            )
            else float(
                "-inf"
            )
        )

        return (
            -timestamp,
            profile.email,
        )

    @staticmethod
    def _index_summary(
        profiles,
    ):
        return {
            "total_profiles":
                len(
                    profiles
                ),

            "with_communication_history":
                sum(
                    1
                    for profile in profiles
                    if (
                        profile
                        .communication_total
                        > 0
                    )
                ),

            "with_pending_commitments":
                sum(
                    1
                    for profile in profiles
                    if (
                        profile
                        .pending_commitments
                        > 0
                    )
                ),

            "with_active_waits":
                sum(
                    1
                    for profile in profiles
                    if (
                        profile
                        .active_waits
                        > 0
                    )
                ),

            "with_decisions":
                sum(
                    1
                    for profile in profiles
                    if (
                        profile
                        .decisions
                        > 0
                    )
                ),
        }
