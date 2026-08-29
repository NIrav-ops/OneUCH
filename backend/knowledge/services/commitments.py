from django.utils import timezone

from knowledge.services.commitment_ledger import (
    CommitmentLedgerService,
)


class CommitmentsService:
    """
    Adoption/API projection over the frozen Commitment Ledger.

    No commitment state is persisted here.

    Business meaning remains owned by CommitmentLedgerService
    and the underlying ActionItem / ExpectedResponseItem
    lifecycle models.
    """

    @classmethod
    def build(
        cls,
        *,
        organization,
    ):
        return (
            CommitmentLedgerService
            .build(
                organization=organization,
            )
        )

    @classmethod
    def summary(
        cls,
        entries,
    ):
        return {
            "total": len(
                entries
            ),

            "pending": sum(
                1
                for entry in entries
                if entry.status == "pending"
            ),

            "fulfilled": sum(
                1
                for entry in entries
                if entry.status == "fulfilled"
            ),

            "ignored": sum(
                1
                for entry in entries
                if entry.status == "ignored"
            ),

            "cancelled": sum(
                1
                for entry in entries
                if entry.status == "cancelled"
            ),

            "we_owe_them": sum(
                1
                for entry in entries
                if (
                    entry.direction
                    ==
                    CommitmentLedgerService
                    .DIRECTION_WE_OWE_THEM
                )
            ),

            "they_owe_us": sum(
                1
                for entry in entries
                if (
                    entry.direction
                    ==
                    CommitmentLedgerService
                    .DIRECTION_THEY_OWE_US
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
        generated_at = (
            now
            or timezone.now()
        )

        entries = cls.build(
            organization=organization,
        )

        return {
            "generated_at": generated_at,

            "organization_id": (
                organization.id
            ),

            "summary": cls.summary(
                entries
            ),

            "items": [
                entry.to_dict()
                for entry in entries
            ],
        }
