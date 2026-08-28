from dataclasses import (
    asdict,
    dataclass,
)
from email.utils import getaddresses
from typing import Optional

from actions.models import (
    ActionItem,
    ExpectedResponseItem,
)

from knowledge.services.commitment_fulfillment import (
    build_commitment_fulfillment,
)

from knowledge.services.commitment_deadlines import (
    build_commitment_deadline_summary,
)

from knowledge.services.intelligence_evidence_builders import (
    build_action_evidence,
    build_expected_response_evidence,
)


@dataclass(frozen=True)
class CommitmentLedgerEntry:
    """
    Normalized read-only One UCH commitment projection.

    This is NOT business-state persistence.

    Source-of-truth remains:

        WE_OWE_THEM
            -> ActionItem

        THEY_OWE_US
            -> ExpectedResponseItem

    The ledger provides one enterprise accountability view
    over both existing lifecycle models.
    """

    commitment_id: str

    direction: str

    organization_id: int
    conversation_id: Optional[int]
    source_message_id: Optional[int]

    source_object_type: str
    source_object_id: int

    obligation: str

    counterparty: Optional[str]

    owner_id: Optional[int]
    owner_email: Optional[str]

    original_due_at: object
    current_due_at: object
    deadline_change_count: int

    status: str
    source_status: str

    created_at: object
    resolved_at: object

    evidence: dict
    fulfillment: dict

    def to_dict(self):
        return asdict(
            self
        )


class CommitmentLedgerService:
    """
    Build One UCH's normalized Commitment Ledger.

    The service intentionally derives state from existing
    ActionItem and ExpectedResponseItem rows instead of
    introducing duplicate commitment persistence.
    """

    DIRECTION_WE_OWE_THEM = (
        "WE_OWE_THEM"
    )

    DIRECTION_THEY_OWE_US = (
        "THEY_OWE_US"
    )

    STATUS_PENDING = "pending"
    STATUS_FULFILLED = "fulfilled"
    STATUS_IGNORED = "ignored"
    STATUS_CANCELLED = "cancelled"

    ACTION_COMMITMENT_SOURCE_TYPES = {
        "email",
        "ai",
    }

    ACTION_PENDING_STATUSES = {
        "open",
        "in_progress",
        "waiting",
        "blocked",
    }

    @classmethod
    def build(
        cls,
        *,
        organization,
    ):
        """
        Return all communication-backed commitments for one
        organization.

        Tenant scoping is mandatory at the initial ORM query.
        """

        action_entries = (
            cls._action_entries(
                organization=organization,
            )
        )

        expected_entries = (
            cls._expected_response_entries(
                organization=organization,
            )
        )

        entries = (
            action_entries
            + expected_entries
        )

        # Stable newest-first ordering. IDs make equal
        # timestamps deterministic.
        return sorted(
            entries,
            key=lambda entry: (
                entry.created_at,
                entry.commitment_id,
            ),
            reverse=True,
        )

    @classmethod
    def _action_entries(
        cls,
        *,
        organization,
    ):
        """
        Communication-backed ActionItems represent
        WE_OWE_THEM.

        Manual/workflow/API/approval-generated Actions are
        deliberately excluded from Commitment Ledger v1
        because their counterparty obligation is not proven
        by the communication evidence contract.
        """

        actions = (
            ActionItem.objects
            .filter(
                organization=organization,
                source_type__in=(
                    cls.ACTION_COMMITMENT_SOURCE_TYPES
                ),
                message__isnull=False,
                message__direction="inbound",
            )
            .select_related(
                "message",
                "message__conversation",
                "owner",
            )
        )

        entries = []

        for action in actions:
            message = action.message

            evidence = (
                build_action_evidence(
                    action
                )
            )

            deadline = (
                build_commitment_deadline_summary(
                    action
                )
            )

            fulfillment = (
                build_commitment_fulfillment(
                    action
                )
            )

            entries.append(
                CommitmentLedgerEntry(
                    commitment_id=(
                        f"action:{action.id}"
                    ),

                    direction=(
                        cls
                        .DIRECTION_WE_OWE_THEM
                    ),

                    organization_id=(
                        action.organization_id
                    ),

                    conversation_id=(
                        message.conversation_id
                    ),

                    source_message_id=(
                        message.id
                    ),

                    source_object_type=(
                        "action"
                    ),

                    source_object_id=(
                        action.id
                    ),

                    obligation=(
                        action.title
                    ),

                    counterparty=(
                        cls._normalize_email(
                            message.sender
                        )
                    ),

                    owner_id=(
                        action.owner_id
                    ),

                    owner_email=(
                        cls._user_email(
                            action.owner
                        )
                    ),

                    original_due_at=(
                        deadline.original_due_at
                    ),

                    current_due_at=(
                        deadline.current_due_at
                    ),

                    deadline_change_count=(
                        deadline.change_count
                    ),

                    status=(
                        cls._action_status(
                            action.status
                        )
                    ),

                    source_status=(
                        action.status
                    ),

                    created_at=(
                        action.created_at
                    ),

                    resolved_at=(
                        action.completed_at
                    ),

                    evidence=(
                        evidence.to_dict()
                    ),

                    fulfillment=(
                        fulfillment.to_dict()
                    ),
                )
            )

        return entries

    @classmethod
    def _expected_response_entries(
        cls,
        *,
        organization,
    ):
        """
        ExpectedResponseItem represents THEY_OWE_US.

        The counterparty is resolved conservatively:

        1. explicit expected_from
        2. inbound sender
        3. first outbound recipient
        """

        items = (
            ExpectedResponseItem.objects
            .filter(
                organization=organization,
            )
            .select_related(
                "source_message",
                "source_message__conversation",
                "user",
            )
        )

        entries = []

        for item in items:
            message = (
                item.source_message
            )

            evidence = (
                build_expected_response_evidence(
                    item
                )
            )

            deadline = (
                build_commitment_deadline_summary(
                    item
                )
            )

            fulfillment = (
                build_commitment_fulfillment(
                    item
                )
            )

            entries.append(
                CommitmentLedgerEntry(
                    commitment_id=(
                        "expected_response:"
                        f"{item.id}"
                    ),

                    direction=(
                        cls
                        .DIRECTION_THEY_OWE_US
                    ),

                    organization_id=(
                        item.organization_id
                    ),

                    conversation_id=(
                        item.conversation_id
                    ),

                    source_message_id=(
                        message.id
                    ),

                    source_object_type=(
                        "expected_response"
                    ),

                    source_object_id=(
                        item.id
                    ),

                    obligation=(
                        item.evidence_text
                        or "Expected response"
                    ),

                    counterparty=(
                        cls
                        ._expected_counterparty(
                            item
                        )
                    ),

                    # The mailbox/user tracking the
                    # obligation is the internal owner.
                    owner_id=(
                        item.user_id
                    ),

                    owner_email=(
                        cls._user_email(
                            item.user
                        )
                    ),

                    original_due_at=(
                        deadline.original_due_at
                    ),

                    current_due_at=(
                        deadline.current_due_at
                    ),

                    deadline_change_count=(
                        deadline.change_count
                    ),

                    status=(
                        cls
                        ._expected_status(
                            item.status
                        )
                    ),

                    source_status=(
                        item.status
                    ),

                    created_at=(
                        item.created_at
                    ),

                    resolved_at=(
                        item.resolved_at
                    ),

                    evidence=(
                        evidence.to_dict()
                    ),

                    fulfillment=(
                        fulfillment.to_dict()
                    ),
                )
            )

        return entries

    @classmethod
    def _action_status(
        cls,
        status,
    ):
        if (
            status
            in cls.ACTION_PENDING_STATUSES
        ):
            return cls.STATUS_PENDING

        if status == "completed":
            return cls.STATUS_FULFILLED

        if status == "ignored":
            return cls.STATUS_IGNORED

        if status == "cancelled":
            return cls.STATUS_CANCELLED

        # Fail conservatively. Do not represent an unknown
        # business state as fulfilled.
        return cls.STATUS_PENDING

    @classmethod
    def _expected_status(
        cls,
        status,
    ):
        if status == "received":
            return cls.STATUS_FULFILLED

        if status == "ignored":
            return cls.STATUS_IGNORED

        return cls.STATUS_PENDING

    @classmethod
    def _expected_counterparty(
        cls,
        item,
    ):
        if item.expected_from:
            return cls._normalize_email(
                item.expected_from
            )

        message = (
            item.source_message
        )

        if message.direction == "inbound":
            return cls._normalize_email(
                message.sender
            )

        return cls._first_recipient(
            message.recipients
        )

    @staticmethod
    def _first_recipient(
        recipients,
    ):
        values = getaddresses(
            [
                recipients or ""
            ]
        )

        for _name, email in values:
            normalized = (
                str(email or "")
                .strip()
                .lower()
            )

            if normalized:
                return normalized

        return None

    @staticmethod
    def _normalize_email(
        value,
    ):
        normalized = (
            str(value or "")
            .strip()
            .lower()
        )

        return (
            normalized
            or None
        )

    @staticmethod
    def _user_email(
        user,
    ):
        if user is None:
            return None

        value = (
            getattr(
                user,
                "email",
                None,
            )
        )

        normalized = (
            str(value or "")
            .strip()
            .lower()
        )

        return (
            normalized
            or None
        )
