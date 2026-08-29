from dataclasses import (
    asdict,
    dataclass,
)
from typing import Optional

from django.utils import timezone

from knowledge.services.commitment_ledger import (
    CommitmentLedgerService,
)


@dataclass(frozen=True)
class WaitingForItem:
    """
    One currently active external obligation.

    Business state is NOT persisted here.

    Waiting For is a focused adoption projection over the
    existing ExpectedResponseItem / Commitment Ledger
    lifecycle.
    """

    waiting_id: str
    commitment_id: str

    organization_id: int

    conversation_id: Optional[int]
    source_message_id: Optional[int]
    source_object_id: int

    obligation: str

    counterparty: Optional[str]

    owner_id: Optional[int]
    owner_email: Optional[str]

    original_due_at: object
    current_due_at: object
    deadline_change_count: int

    due_state: str

    source_status: str

    created_at: object

    evidence: dict

    open_url: Optional[str]

    def to_dict(self):
        return asdict(
            self
        )


class WaitingForService:
    """
    Read-only active external accountability projection.

    Inclusion rules are intentionally strict:

        direction
            THEY_OWE_US

        normalized ledger status
            pending

        underlying ExpectedResponseItem status
            waiting

    Received and ignored items belong to historical
    Commitments, not the active Waiting For queue.
    """

    DUE_OVERDUE = "overdue"
    DUE_TODAY = "due_today"
    DUE_UPCOMING = "upcoming"
    DUE_NONE = "no_due"

    DUE_STATE_ORDER = {
        DUE_OVERDUE: 0,
        DUE_TODAY: 1,
        DUE_UPCOMING: 2,
        DUE_NONE: 3,
    }

    @classmethod
    def build(
        cls,
        *,
        organization,
        now=None,
    ):
        effective_now = (
            now
            or timezone.now()
        )

        ledger = (
            CommitmentLedgerService
            .build(
                organization=organization,
            )
        )

        items = []

        for entry in ledger:

            if (
                entry.direction
                !=
                CommitmentLedgerService
                .DIRECTION_THEY_OWE_US
            ):
                continue

            if (
                entry.source_object_type
                != "expected_response"
            ):
                continue

            if (
                entry.status
                !=
                CommitmentLedgerService
                .STATUS_PENDING
            ):
                continue

            if (
                entry.source_status
                != "waiting"
            ):
                continue

            due_state = (
                cls._due_state(
                    entry.current_due_at,
                    now=effective_now,
                )
            )

            items.append(
                WaitingForItem(
                    waiting_id=(
                        "waiting_for:"
                        f"{entry.source_object_id}"
                    ),

                    commitment_id=(
                        entry.commitment_id
                    ),

                    organization_id=(
                        entry.organization_id
                    ),

                    conversation_id=(
                        entry.conversation_id
                    ),

                    source_message_id=(
                        entry.source_message_id
                    ),

                    source_object_id=(
                        entry.source_object_id
                    ),

                    obligation=(
                        entry.obligation
                    ),

                    counterparty=(
                        entry.counterparty
                    ),

                    owner_id=(
                        entry.owner_id
                    ),

                    owner_email=(
                        entry.owner_email
                    ),

                    original_due_at=(
                        entry.original_due_at
                    ),

                    current_due_at=(
                        entry.current_due_at
                    ),

                    deadline_change_count=(
                        entry.deadline_change_count
                    ),

                    due_state=(
                        due_state
                    ),

                    source_status=(
                        entry.source_status
                    ),

                    created_at=(
                        entry.created_at
                    ),

                    evidence=(
                        entry.evidence
                    ),

                    open_url=(
                        cls._open_url(
                            entry.conversation_id
                        )
                    ),
                )
            )

        return sorted(
            items,
            key=cls._sort_key,
        )

    @classmethod
    def summary(
        cls,
        items,
    ):
        return {
            "total": len(
                items
            ),

            "overdue": sum(
                1
                for item in items
                if (
                    item.due_state
                    == cls.DUE_OVERDUE
                )
            ),

            "due_today": sum(
                1
                for item in items
                if (
                    item.due_state
                    == cls.DUE_TODAY
                )
            ),

            "upcoming": sum(
                1
                for item in items
                if (
                    item.due_state
                    == cls.DUE_UPCOMING
                )
            ),

            "no_due": sum(
                1
                for item in items
                if (
                    item.due_state
                    == cls.DUE_NONE
                )
            ),
        }

    @classmethod
    def build_payload(
        cls,
        *,
        organization,
        now=None,
    ):
        effective_now = (
            now
            or timezone.now()
        )

        items = cls.build(
            organization=organization,
            now=effective_now,
        )

        return {
            "generated_at": (
                effective_now
            ),

            "organization_id": (
                organization.id
            ),

            "summary": (
                cls.summary(
                    items
                )
            ),

            "items": [
                item.to_dict()
                for item in items
            ],
        }

    @classmethod
    def _due_state(
        cls,
        due_at,
        *,
        now,
    ):
        if due_at is None:
            return cls.DUE_NONE

        if due_at < now:
            return cls.DUE_OVERDUE

        if (
            timezone.localdate(
                due_at
            )
            ==
            timezone.localdate(
                now
            )
        ):
            return cls.DUE_TODAY

        return cls.DUE_UPCOMING

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

    @classmethod
    def _sort_key(
        cls,
        item,
    ):
        due_value = (
            item.current_due_at.timestamp()
            if item.current_due_at
            is not None
            else float("inf")
        )

        created_value = (
            item.created_at.timestamp()
            if item.created_at
            is not None
            else float("inf")
        )

        return (
            cls.DUE_STATE_ORDER[
                item.due_state
            ],
            due_value,
            created_value,
            item.waiting_id,
        )
