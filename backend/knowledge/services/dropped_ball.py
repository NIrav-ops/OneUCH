from dataclasses import (
    asdict,
    dataclass,
)
from typing import Optional

from django.utils import timezone

from knowledge.services.commitment_ledger import (
    CommitmentLedgerService,
)
from knowledge.services.communication_sla import (
    CommunicationSLAService,
)
from knowledge.services.ownership_gap import (
    OwnershipGapService,
)


@dataclass(frozen=True)
class DroppedBallFinding:
    """
    Read-only One UCH Dropped Ball intelligence.

    This represents a proven missed accountability boundary.

    It does NOT persist duplicate business state.
    """

    finding_id: str

    commitment_id: str
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
    sla_state: Optional[str]

    ownership_gap_type: Optional[str]
    ownership_reason_code: Optional[str]

    reason_code: str
    reason: str

    signal_codes: tuple

    evidence: dict

    def to_dict(self):
        return asdict(
            self
        )


class DroppedBallService:
    """
    Derive current Dropped Ball findings.

    Internal responsibility:

        WE_OWE_THEM + pending
        AND
        (
            communication SLA breached
            OR
            commitment deadline overdue
        )

    Ownership gaps strengthen the finding but do not create
    a Dropped Ball by themselves.

    External responsibility:

        THEY_OWE_US + pending
        AND
        explicit response deadline overdue

    The external case is clearly marked as counterparty
    responsibility so One UCH does not falsely blame an
    internal owner.
    """

    RESPONSIBILITY_INTERNAL = (
        "internal"
    )

    RESPONSIBILITY_COUNTERPARTY = (
        "counterparty"
    )

    REASON_INTERNAL_SLA_BREACHED = (
        "INTERNAL_COMMUNICATION_SLA_BREACHED"
    )

    REASON_INTERNAL_DEADLINE_MISSED = (
        "INTERNAL_COMMITMENT_DEADLINE_MISSED"
    )

    REASON_INTERNAL_SLA_AND_DEADLINE = (
        "INTERNAL_SLA_AND_COMMITMENT_DEADLINE_MISSED"
    )

    REASON_COUNTERPARTY_RESPONSE_OVERDUE = (
        "COUNTERPARTY_RESPONSE_OVERDUE"
    )

    SIGNAL_SLA_BREACHED = (
        "COMMUNICATION_SLA_BREACHED"
    )

    SIGNAL_COMMITMENT_OVERDUE = (
        "COMMITMENT_DEADLINE_OVERDUE"
    )

    SIGNAL_COUNTERPARTY_OVERDUE = (
        "COUNTERPARTY_RESPONSE_DEADLINE_OVERDUE"
    )

    @classmethod
    def build(
        cls,
        *,
        organization,
        now=None,
        sla_policy=None,
    ):
        """
        Return current organization-scoped Dropped Ball
        findings.
        """

        effective_now = (
            now
            or timezone.now()
        )

        commitments = (
            CommitmentLedgerService.build(
                organization=organization,
            )
        )

        sla_findings = (
            CommunicationSLAService.build(
                organization=organization,
                policy=sla_policy,
                now=effective_now,
            )
        )

        ownership_findings = (
            OwnershipGapService.build(
                organization=organization,
            )
        )

        sla_by_commitment = {
            finding.commitment_id: finding
            for finding in sla_findings
        }

        ownership_by_commitment = {
            finding.commitment_id: finding
            for finding in ownership_findings
        }

        findings = []

        for commitment in commitments:

            if (
                commitment.status
                != (
                    CommitmentLedgerService
                    .STATUS_PENDING
                )
            ):
                continue

            if (
                commitment.direction
                == (
                    CommitmentLedgerService
                    .DIRECTION_WE_OWE_THEM
                )
            ):
                finding = (
                    cls._internal_finding(
                        commitment=commitment,
                        sla_finding=(
                            sla_by_commitment.get(
                                commitment.commitment_id
                            )
                        ),
                        ownership_finding=(
                            ownership_by_commitment.get(
                                commitment.commitment_id
                            )
                        ),
                        now=effective_now,
                    )
                )

            elif (
                commitment.direction
                == (
                    CommitmentLedgerService
                    .DIRECTION_THEY_OWE_US
                )
            ):
                finding = (
                    cls._counterparty_finding(
                        commitment=commitment,
                        now=effective_now,
                    )
                )

            else:
                finding = None

            if finding is not None:
                findings.append(
                    finding
                )

        return findings

    @classmethod
    def _internal_finding(
        cls,
        *,
        commitment,
        sla_finding,
        ownership_finding,
        now,
    ):
        sla_breached = (
            sla_finding is not None
            and sla_finding.state
            == (
                CommunicationSLAService
                .STATE_BREACHED
            )
        )

        commitment_overdue = (
            commitment.current_due_at
            is not None
            and commitment.current_due_at
            < now
        )

        # Ownership gap is not enough by itself.
        if (
            not sla_breached
            and not commitment_overdue
        ):
            return None

        signals = []

        if sla_breached:
            signals.append(
                cls.SIGNAL_SLA_BREACHED
            )

        if commitment_overdue:
            signals.append(
                cls.SIGNAL_COMMITMENT_OVERDUE
            )

        if ownership_finding is not None:
            signals.append(
                ownership_finding.reason_code
            )

        if (
            sla_breached
            and commitment_overdue
        ):
            reason_code = (
                cls
                .REASON_INTERNAL_SLA_AND_DEADLINE
            )

            reason = (
                "Internal communication commitment "
                "has breached both its communication "
                "SLA and commitment deadline."
            )

        elif commitment_overdue:
            reason_code = (
                cls
                .REASON_INTERNAL_DEADLINE_MISSED
            )

            reason = (
                "Internal communication commitment "
                "has passed its commitment deadline."
            )

        else:
            reason_code = (
                cls
                .REASON_INTERNAL_SLA_BREACHED
            )

            reason = (
                "Internal communication commitment "
                "has exceeded its communication SLA."
            )

        return DroppedBallFinding(
            finding_id=(
                "dropped_ball:"
                f"{commitment.commitment_id}"
            ),

            commitment_id=(
                commitment.commitment_id
            ),

            direction=(
                commitment.direction
            ),

            responsibility_side=(
                cls.RESPONSIBILITY_INTERNAL
            ),

            organization_id=(
                commitment.organization_id
            ),

            conversation_id=(
                commitment.conversation_id
            ),

            source_message_id=(
                commitment.source_message_id
            ),

            source_object_type=(
                commitment.source_object_type
            ),

            source_object_id=(
                commitment.source_object_id
            ),

            obligation=(
                commitment.obligation
            ),

            counterparty=(
                commitment.counterparty
            ),

            owner_id=(
                commitment.owner_id
            ),

            owner_email=(
                commitment.owner_email
            ),

            commitment_due_at=(
                commitment.current_due_at
            ),

            sla_due_at=(
                sla_finding.sla_due_at
                if sla_finding is not None
                else None
            ),

            sla_state=(
                sla_finding.state
                if sla_finding is not None
                else None
            ),

            ownership_gap_type=(
                ownership_finding.gap_type
                if ownership_finding
                is not None
                else None
            ),

            ownership_reason_code=(
                ownership_finding.reason_code
                if ownership_finding
                is not None
                else None
            ),

            reason_code=(
                reason_code
            ),

            reason=(
                reason
            ),

            signal_codes=tuple(
                signals
            ),

            evidence=(
                commitment.evidence
            ),
        )

    @classmethod
    def _counterparty_finding(
        cls,
        *,
        commitment,
        now,
    ):
        due_at = (
            commitment.current_due_at
        )

        if (
            due_at is None
            or due_at >= now
        ):
            return None

        return DroppedBallFinding(
            finding_id=(
                "dropped_ball:"
                f"{commitment.commitment_id}"
            ),

            commitment_id=(
                commitment.commitment_id
            ),

            direction=(
                commitment.direction
            ),

            responsibility_side=(
                cls
                .RESPONSIBILITY_COUNTERPARTY
            ),

            organization_id=(
                commitment.organization_id
            ),

            conversation_id=(
                commitment.conversation_id
            ),

            source_message_id=(
                commitment.source_message_id
            ),

            source_object_type=(
                commitment.source_object_type
            ),

            source_object_id=(
                commitment.source_object_id
            ),

            obligation=(
                commitment.obligation
            ),

            counterparty=(
                commitment.counterparty
            ),

            owner_id=(
                commitment.owner_id
            ),

            owner_email=(
                commitment.owner_email
            ),

            commitment_due_at=(
                due_at
            ),

            sla_due_at=None,
            sla_state=None,

            ownership_gap_type=None,
            ownership_reason_code=None,

            reason_code=(
                cls
                .REASON_COUNTERPARTY_RESPONSE_OVERDUE
            ),

            reason=(
                "Expected counterparty response "
                "has passed its explicit response "
                "deadline."
            ),

            signal_codes=(
                cls
                .SIGNAL_COUNTERPARTY_OVERDUE,
            ),

            evidence=(
                commitment.evidence
            ),
        )
