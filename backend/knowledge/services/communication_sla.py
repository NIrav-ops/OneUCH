from dataclasses import (
    asdict,
    dataclass,
)
from datetime import timedelta
from typing import Optional

from django.utils import timezone

from actions.models import ActionItem

from knowledge.services.commitment_ledger import (
    CommitmentLedgerService,
)


@dataclass(frozen=True)
class CommunicationSLAPolicy:
    """
    MVP system-level SLA policy.

    This intentionally lives outside database persistence.

    Tenant-specific SLA policy may replace this later without
    changing the SLA evaluation contract.
    """

    target_minutes: int = 240
    at_risk_minutes: int = 60

    def __post_init__(self):
        if self.target_minutes <= 0:
            raise ValueError(
                "target_minutes must be greater than zero."
            )

        if self.at_risk_minutes < 0:
            raise ValueError(
                "at_risk_minutes cannot be negative."
            )

        if (
            self.at_risk_minutes
            > self.target_minutes
        ):
            raise ValueError(
                "at_risk_minutes cannot exceed "
                "target_minutes."
            )


@dataclass(frozen=True)
class CommunicationSLAFinding:
    """
    Read-only One UCH communication SLA projection.

    No duplicate SLA business state is persisted.
    """

    sla_id: str

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

    commitment_due_at: object

    sla_started_at: object
    sla_due_at: object

    policy_target_minutes: int
    policy_at_risk_minutes: int

    state: str
    reason_code: str
    reason: str

    seconds_remaining: int
    breached_by_seconds: int

    fulfilled_at: object

    evidence: dict

    def to_dict(self):
        return asdict(
            self
        )


class CommunicationSLAService:
    """
    Evaluate communication responsiveness for internal
    obligations.

    MVP rules:

    - WE_OWE_THEM only.
    - ignored/cancelled commitments are excluded.
    - SLA clock starts from source communication received_at.
    - pending items may be on_track / at_risk / breached.
    - fulfilled items retain historical SLA result:
        met
        breached
    """

    STATE_ON_TRACK = "on_track"
    STATE_AT_RISK = "at_risk"
    STATE_BREACHED = "breached"
    STATE_MET = "met"

    REASON_ON_TRACK = (
        "COMMUNICATION_SLA_ON_TRACK"
    )

    REASON_AT_RISK = (
        "COMMUNICATION_SLA_AT_RISK"
    )

    REASON_BREACHED = (
        "COMMUNICATION_SLA_BREACHED"
    )

    REASON_BREACHED_LATE = (
        "COMMUNICATION_SLA_BREACHED_LATE"
    )

    REASON_MET = (
        "COMMUNICATION_SLA_MET"
    )

    DEFAULT_POLICY = (
        CommunicationSLAPolicy()
    )

    @classmethod
    def build(
        cls,
        *,
        organization,
        policy=None,
        now=None,
    ):
        """
        Return organization-scoped SLA findings.

        now is injectable so SLA evaluation remains
        deterministic in tests and batch processing.
        """

        resolved_policy = (
            policy
            or cls.DEFAULT_POLICY
        )

        effective_now = (
            now
            or timezone.now()
        )

        commitments = (
            CommitmentLedgerService.build(
                organization=organization,
            )
        )

        eligible = [
            commitment
            for commitment in commitments
            if (
                commitment.direction
                == (
                    CommitmentLedgerService
                    .DIRECTION_WE_OWE_THEM
                )
                and commitment.status
                not in {
                    CommitmentLedgerService
                    .STATUS_IGNORED,
                    CommitmentLedgerService
                    .STATUS_CANCELLED,
                }
            )
        ]

        action_ids = [
            commitment.source_object_id
            for commitment in eligible
            if (
                commitment.source_object_type
                == "action"
            )
        ]

        actions = {
            action.id: action
            for action in (
                ActionItem.objects
                .filter(
                    organization=organization,
                    id__in=action_ids,
                )
                .select_related(
                    "message",
                )
            )
        }

        findings = []

        for commitment in eligible:
            action = actions.get(
                commitment.source_object_id
            )

            if action is None:
                continue

            message = action.message

            sla_started_at = (
                message.received_at
                if message is not None
                else commitment.created_at
            )

            sla_due_at = (
                sla_started_at
                + timedelta(
                    minutes=(
                        resolved_policy
                        .target_minutes
                    )
                )
            )

            fulfillment = (
                commitment.fulfillment
                if isinstance(
                    commitment.fulfillment,
                    dict,
                )
                else {}
            )

            fulfilled_at = (
                fulfillment.get(
                    "fulfilled_at"
                )
            )

            (
                state,
                reason_code,
                reason,
                seconds_remaining,
                breached_by_seconds,
            ) = cls._evaluate(
                commitment_status=(
                    commitment.status
                ),
                fulfilled_at=(
                    fulfilled_at
                ),
                sla_due_at=(
                    sla_due_at
                ),
                now=(
                    effective_now
                ),
                policy=(
                    resolved_policy
                ),
            )

            findings.append(
                CommunicationSLAFinding(
                    sla_id=(
                        "communication_sla:"
                        f"{commitment.commitment_id}"
                    ),

                    commitment_id=(
                        commitment.commitment_id
                    ),

                    direction=(
                        commitment.direction
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
                        commitment
                        .source_object_type
                    ),

                    source_object_id=(
                        commitment
                        .source_object_id
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
                        commitment
                        .current_due_at
                    ),

                    sla_started_at=(
                        sla_started_at
                    ),

                    sla_due_at=(
                        sla_due_at
                    ),

                    policy_target_minutes=(
                        resolved_policy
                        .target_minutes
                    ),

                    policy_at_risk_minutes=(
                        resolved_policy
                        .at_risk_minutes
                    ),

                    state=state,

                    reason_code=(
                        reason_code
                    ),

                    reason=reason,

                    seconds_remaining=(
                        seconds_remaining
                    ),

                    breached_by_seconds=(
                        breached_by_seconds
                    ),

                    fulfilled_at=(
                        fulfilled_at
                    ),

                    evidence=(
                        commitment.evidence
                    ),
                )
            )

        return findings

    @classmethod
    def _evaluate(
        cls,
        *,
        commitment_status,
        fulfilled_at,
        sla_due_at,
        now,
        policy,
    ):
        """
        Evaluate current or historical SLA state.
        """

        # ----------------------------------------------------
        # Historical fulfilled commitment.
        # ----------------------------------------------------

        if (
            commitment_status
            == (
                CommitmentLedgerService
                .STATUS_FULFILLED
            )
        ):
            if fulfilled_at is None:
                # We know it was fulfilled, but do not invent
                # a completion timestamp.
                return (
                    cls.STATE_MET,
                    cls.REASON_MET,
                    (
                        "Commitment is fulfilled; "
                        "exact fulfillment time is "
                        "not available."
                    ),
                    0,
                    0,
                )

            if fulfilled_at <= sla_due_at:
                return (
                    cls.STATE_MET,
                    cls.REASON_MET,
                    (
                        "Communication commitment "
                        "was fulfilled within SLA."
                    ),
                    0,
                    0,
                )

            breached_by = int(
                (
                    fulfilled_at
                    - sla_due_at
                ).total_seconds()
            )

            return (
                cls.STATE_BREACHED,
                cls.REASON_BREACHED_LATE,
                (
                    "Communication commitment "
                    "was fulfilled after SLA."
                ),
                0,
                max(
                    breached_by,
                    0,
                ),
            )

        # ----------------------------------------------------
        # Current pending commitment.
        # ----------------------------------------------------

        delta_seconds = int(
            (
                sla_due_at
                - now
            ).total_seconds()
        )

        if delta_seconds < 0:
            return (
                cls.STATE_BREACHED,
                cls.REASON_BREACHED,
                (
                    "Communication commitment "
                    "has exceeded its SLA."
                ),
                0,
                abs(
                    delta_seconds
                ),
            )

        at_risk_seconds = (
            policy.at_risk_minutes
            * 60
        )

        if (
            delta_seconds
            <= at_risk_seconds
        ):
            return (
                cls.STATE_AT_RISK,
                cls.REASON_AT_RISK,
                (
                    "Communication commitment "
                    "is approaching its SLA "
                    "deadline."
                ),
                delta_seconds,
                0,
            )

        return (
            cls.STATE_ON_TRACK,
            cls.REASON_ON_TRACK,
            (
                "Communication commitment "
                "is within SLA."
            ),
            delta_seconds,
            0,
        )
