from dataclasses import (
    asdict,
    dataclass,
)
from typing import Optional

from inbox.models import (
    OrganizationUser,
)

from knowledge.services.commitment_ledger import (
    CommitmentLedgerService,
)


@dataclass(frozen=True)
class OwnershipGapFinding:
    """
    Read-only One UCH ownership-gap finding.

    This is derived intelligence, not another business-state
    model.

    Source of truth remains the Commitment Ledger /
    underlying ActionItem.
    """

    finding_id: str

    commitment_id: str
    direction: str

    organization_id: int
    conversation_id: Optional[int]
    source_message_id: Optional[int]

    source_object_type: str
    source_object_id: int

    obligation: str
    counterparty: Optional[str]

    current_owner_id: Optional[int]
    current_owner_email: Optional[str]

    current_due_at: object
    status: str

    gap_type: str
    reason_code: str
    reason: str

    evidence: dict

    def to_dict(self):
        return asdict(
            self
        )


class OwnershipGapService:
    """
    Detect active internal commitments that do not have a
    valid explicit owner.

    Rules:

    1. Only WE_OWE_THEM commitments participate.
    2. Commitment must still be pending.
    3. owner=None is an ownership gap.
    4. Owner outside the organization is also a gap.
    5. THEY_OWE_US is not considered unowned merely because
       the external counterparty owes the organization.
    """

    GAP_TYPE_UNASSIGNED = (
        "unassigned"
    )

    GAP_TYPE_INVALID_OWNER = (
        "invalid_owner"
    )

    REASON_NO_EXPLICIT_OWNER = (
        "NO_EXPLICIT_OWNER"
    )

    REASON_OWNER_OUTSIDE_ORGANIZATION = (
        "OWNER_OUTSIDE_ORGANIZATION"
    )

    @classmethod
    def build(
        cls,
        *,
        organization,
    ):
        """
        Return current organization-scoped ownership gaps.

        Findings are intentionally derived on read. Assigning
        a valid owner automatically resolves the gap without a
        second persistence lifecycle.
        """

        valid_owner_ids = set(
            OrganizationUser.objects
            .filter(
                organization=organization,
            )
            .values_list(
                "user_id",
                flat=True,
            )
        )

        commitments = (
            CommitmentLedgerService.build(
                organization=organization,
            )
        )

        findings = []

        for commitment in commitments:

            # -----------------------------------------------
            # Only our own outstanding obligations can have
            # an internal execution ownership gap.
            # -----------------------------------------------

            if (
                commitment.direction
                != (
                    CommitmentLedgerService
                    .DIRECTION_WE_OWE_THEM
                )
            ):
                continue

            if (
                commitment.status
                != (
                    CommitmentLedgerService
                    .STATUS_PENDING
                )
            ):
                continue

            gap_type = None
            reason_code = None
            reason = None

            if commitment.owner_id is None:
                gap_type = (
                    cls.GAP_TYPE_UNASSIGNED
                )

                reason_code = (
                    cls
                    .REASON_NO_EXPLICIT_OWNER
                )

                reason = (
                    "Pending communication commitment "
                    "has no explicit internal owner."
                )

            elif (
                commitment.owner_id
                not in valid_owner_ids
            ):
                gap_type = (
                    cls.GAP_TYPE_INVALID_OWNER
                )

                reason_code = (
                    cls
                    .REASON_OWNER_OUTSIDE_ORGANIZATION
                )

                reason = (
                    "Assigned owner is not a member "
                    "of this organization."
                )

            else:
                continue

            findings.append(
                OwnershipGapFinding(
                    finding_id=(
                        "ownership_gap:"
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

                    current_owner_id=(
                        commitment.owner_id
                    ),

                    current_owner_email=(
                        commitment.owner_email
                    ),

                    current_due_at=(
                        commitment.current_due_at
                    ),

                    status=(
                        commitment.status
                    ),

                    gap_type=(
                        gap_type
                    ),

                    reason_code=(
                        reason_code
                    ),

                    reason=(
                        reason
                    ),

                    evidence=(
                        commitment.evidence
                    ),
                )
            )

        return findings
