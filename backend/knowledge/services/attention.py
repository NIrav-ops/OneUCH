from dataclasses import (
    asdict,
    dataclass,
)
from typing import Optional

from django.utils import timezone

from knowledge.services.communication_sla import (
    CommunicationSLAService,
)
from knowledge.services.dropped_ball import (
    DroppedBallService,
)
from knowledge.services.ownership_gap import (
    OwnershipGapService,
)


@dataclass(frozen=True)
class AttentionItem:
    """
    One current actionable One UCH attention item.

    Multiple underlying intelligence signals for the same
    commitment are deliberately collapsed into one item.
    """

    attention_id: str
    commitment_id: str

    category: str
    severity: str

    direction: str
    responsibility_side: str

    organization_id: int
    conversation_id: Optional[int]
    source_message_id: Optional[int]

    source_object_type: str
    source_object_id: int

    obligation: str
    counterparty: Optional[str]

    owner_id: Optional[int]
    owner_email: Optional[str]

    commitment_due_at: object
    sla_due_at: object

    reason_code: str
    reason: str

    ownership_gap_type: Optional[str]
    ownership_reason_code: Optional[str]

    signal_codes: tuple

    evidence: dict

    def to_dict(self):
        return asdict(
            self
        )


class AttentionService:
    """
    Aggregate current accountability intelligence into a
    single actionable organization-scoped attention surface.

    Precedence:

        dropped_ball
            >
        sla_at_risk
            >
        ownership_gap

    A commitment appears at most once.
    """

    CATEGORY_DROPPED_BALL = (
        "dropped_ball"
    )

    CATEGORY_SLA_AT_RISK = (
        "sla_at_risk"
    )

    CATEGORY_OWNERSHIP_GAP = (
        "ownership_gap"
    )

    SEVERITY_CRITICAL = "critical"
    SEVERITY_HIGH = "high"
    SEVERITY_MEDIUM = "medium"

    RESPONSIBILITY_INTERNAL = (
        "internal"
    )

    RESPONSIBILITY_COUNTERPARTY = (
        "counterparty"
    )

    SEVERITY_ORDER = {
        SEVERITY_CRITICAL: 0,
        SEVERITY_HIGH: 1,
        SEVERITY_MEDIUM: 2,
    }

    @classmethod
    def build(
        cls,
        *,
        organization,
        now=None,
        sla_policy=None,
    ):
        effective_now = (
            now
            or timezone.now()
        )

        dropped = (
            DroppedBallService.build(
                organization=organization,
                now=effective_now,
                sla_policy=sla_policy,
            )
        )

        sla_findings = (
            CommunicationSLAService.build(
                organization=organization,
                now=effective_now,
                policy=sla_policy,
            )
        )

        ownership_findings = (
            OwnershipGapService.build(
                organization=organization,
            )
        )

        ownership_by_commitment = {
            finding.commitment_id: finding
            for finding in ownership_findings
        }

        items = []
        consumed = set()

        # ----------------------------------------------------
        # 1. Dropped Ball always dominates.
        # ----------------------------------------------------

        for finding in dropped:
            ownership = (
                ownership_by_commitment.get(
                    finding.commitment_id
                )
            )

            severity = (
                cls.SEVERITY_CRITICAL
                if (
                    finding.responsibility_side
                    == cls.RESPONSIBILITY_INTERNAL
                )
                else cls.SEVERITY_HIGH
            )

            signals = list(
                finding.signal_codes
            )

            if (
                ownership is not None
                and ownership.reason_code
                not in signals
            ):
                signals.append(
                    ownership.reason_code
                )

            items.append(
                AttentionItem(
                    attention_id=(
                        "attention:"
                        f"{finding.commitment_id}"
                    ),

                    commitment_id=(
                        finding.commitment_id
                    ),

                    category=(
                        cls.CATEGORY_DROPPED_BALL
                    ),

                    severity=severity,

                    direction=(
                        finding.direction
                    ),

                    responsibility_side=(
                        finding.responsibility_side
                    ),

                    organization_id=(
                        finding.organization_id
                    ),

                    conversation_id=(
                        finding.conversation_id
                    ),

                    source_message_id=(
                        finding.source_message_id
                    ),

                    source_object_type=(
                        finding.source_object_type
                    ),

                    source_object_id=(
                        finding.source_object_id
                    ),

                    obligation=(
                        finding.obligation
                    ),

                    counterparty=(
                        finding.counterparty
                    ),

                    owner_id=(
                        finding.owner_id
                    ),

                    owner_email=(
                        finding.owner_email
                    ),

                    commitment_due_at=(
                        finding.commitment_due_at
                    ),

                    sla_due_at=(
                        finding.sla_due_at
                    ),

                    reason_code=(
                        finding.reason_code
                    ),

                    reason=(
                        finding.reason
                    ),

                    ownership_gap_type=(
                        finding.ownership_gap_type
                    ),

                    ownership_reason_code=(
                        finding
                        .ownership_reason_code
                    ),

                    signal_codes=tuple(
                        signals
                    ),

                    evidence=(
                        finding.evidence
                    ),
                )
            )

            consumed.add(
                finding.commitment_id
            )

        # ----------------------------------------------------
        # 2. Only current AT-RISK SLA items are independently
        #    actionable.
        #
        #    Breached pending commitments are already Dropped
        #    Ball findings. Historical fulfilled breaches must
        #    not become current Attention items.
        # ----------------------------------------------------

        for finding in sla_findings:

            if (
                finding.commitment_id
                in consumed
            ):
                continue

            if (
                finding.state
                != (
                    CommunicationSLAService
                    .STATE_AT_RISK
                )
            ):
                continue

            ownership = (
                ownership_by_commitment.get(
                    finding.commitment_id
                )
            )

            signals = [
                finding.reason_code
            ]

            ownership_gap_type = None
            ownership_reason_code = None

            if ownership is not None:
                ownership_gap_type = (
                    ownership.gap_type
                )

                ownership_reason_code = (
                    ownership.reason_code
                )

                if (
                    ownership.reason_code
                    not in signals
                ):
                    signals.append(
                        ownership.reason_code
                    )

            items.append(
                AttentionItem(
                    attention_id=(
                        "attention:"
                        f"{finding.commitment_id}"
                    ),

                    commitment_id=(
                        finding.commitment_id
                    ),

                    category=(
                        cls.CATEGORY_SLA_AT_RISK
                    ),

                    severity=(
                        cls.SEVERITY_HIGH
                    ),

                    direction=(
                        finding.direction
                    ),

                    responsibility_side=(
                        cls.RESPONSIBILITY_INTERNAL
                    ),

                    organization_id=(
                        finding.organization_id
                    ),

                    conversation_id=(
                        finding.conversation_id
                    ),

                    source_message_id=(
                        finding.source_message_id
                    ),

                    source_object_type=(
                        finding.source_object_type
                    ),

                    source_object_id=(
                        finding.source_object_id
                    ),

                    obligation=(
                        finding.obligation
                    ),

                    counterparty=(
                        finding.counterparty
                    ),

                    owner_id=(
                        finding.owner_id
                    ),

                    owner_email=(
                        finding.owner_email
                    ),

                    commitment_due_at=(
                        finding.commitment_due_at
                    ),

                    sla_due_at=(
                        finding.sla_due_at
                    ),

                    reason_code=(
                        finding.reason_code
                    ),

                    reason=(
                        finding.reason
                    ),

                    ownership_gap_type=(
                        ownership_gap_type
                    ),

                    ownership_reason_code=(
                        ownership_reason_code
                    ),

                    signal_codes=tuple(
                        signals
                    ),

                    evidence=(
                        finding.evidence
                    ),
                )
            )

            consumed.add(
                finding.commitment_id
            )

        # ----------------------------------------------------
        # 3. Remaining ownership gaps.
        # ----------------------------------------------------

        for finding in ownership_findings:

            if (
                finding.commitment_id
                in consumed
            ):
                continue

            items.append(
                AttentionItem(
                    attention_id=(
                        "attention:"
                        f"{finding.commitment_id}"
                    ),

                    commitment_id=(
                        finding.commitment_id
                    ),

                    category=(
                        cls.CATEGORY_OWNERSHIP_GAP
                    ),

                    severity=(
                        cls.SEVERITY_MEDIUM
                    ),

                    direction=(
                        finding.direction
                    ),

                    responsibility_side=(
                        cls.RESPONSIBILITY_INTERNAL
                    ),

                    organization_id=(
                        finding.organization_id
                    ),

                    conversation_id=(
                        finding.conversation_id
                    ),

                    source_message_id=(
                        finding.source_message_id
                    ),

                    source_object_type=(
                        finding.source_object_type
                    ),

                    source_object_id=(
                        finding.source_object_id
                    ),

                    obligation=(
                        finding.obligation
                    ),

                    counterparty=(
                        finding.counterparty
                    ),

                    owner_id=(
                        finding.current_owner_id
                    ),

                    owner_email=(
                        finding.current_owner_email
                    ),

                    commitment_due_at=(
                        finding.current_due_at
                    ),

                    sla_due_at=None,

                    reason_code=(
                        finding.reason_code
                    ),

                    reason=(
                        finding.reason
                    ),

                    ownership_gap_type=(
                        finding.gap_type
                    ),

                    ownership_reason_code=(
                        finding.reason_code
                    ),

                    signal_codes=(
                        finding.reason_code,
                    ),

                    evidence=(
                        finding.evidence
                    ),
                )
            )

            consumed.add(
                finding.commitment_id
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
            "total": len(items),

            "critical": sum(
                1
                for item in items
                if (
                    item.severity
                    == cls.SEVERITY_CRITICAL
                )
            ),

            "high": sum(
                1
                for item in items
                if (
                    item.severity
                    == cls.SEVERITY_HIGH
                )
            ),

            "medium": sum(
                1
                for item in items
                if (
                    item.severity
                    == cls.SEVERITY_MEDIUM
                )
            ),

            "dropped_ball": sum(
                1
                for item in items
                if (
                    item.category
                    == cls.CATEGORY_DROPPED_BALL
                )
            ),

            "sla_at_risk": sum(
                1
                for item in items
                if (
                    item.category
                    == cls.CATEGORY_SLA_AT_RISK
                )
            ),

            "ownership_gap": sum(
                1
                for item in items
                if (
                    item.category
                    == cls.CATEGORY_OWNERSHIP_GAP
                )
            ),

            "internal": sum(
                1
                for item in items
                if (
                    item.responsibility_side
                    == cls.RESPONSIBILITY_INTERNAL
                )
            ),

            "counterparty": sum(
                1
                for item in items
                if (
                    item.responsibility_side
                    == (
                        cls
                        .RESPONSIBILITY_COUNTERPARTY
                    )
                )
            ),
        }

    @classmethod
    def build_payload(
        cls,
        *,
        organization,
        now=None,
        sla_policy=None,
    ):
        effective_now = (
            now
            or timezone.now()
        )

        items = cls.build(
            organization=organization,
            now=effective_now,
            sla_policy=sla_policy,
        )

        return {
            "generated_at": effective_now,

            "organization_id": (
                organization.id
            ),

            "summary": cls.summary(
                items
            ),

            "items": [
                item.to_dict()
                for item in items
            ],
        }

    @classmethod
    def _sort_key(
        cls,
        item,
    ):
        deadline = (
            item.sla_due_at
            or item.commitment_due_at
        )

        deadline_value = (
            deadline.timestamp()
            if deadline is not None
            else float("inf")
        )

        return (
            cls.SEVERITY_ORDER[
                item.severity
            ],
            deadline_value,
            item.attention_id,
        )
