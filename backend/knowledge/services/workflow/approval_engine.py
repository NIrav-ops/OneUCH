from approvals.models import ApprovalItem

from knowledge.services.workflow.base_workflow_engine import (
    BaseWorkflowEngine,
)


class ApprovalEngine(
    BaseWorkflowEngine,
):

    category = "approvals"

    PENDING_STATUSES = (
        "pending",
        "needs_info",
    )

    def build(
        self,
        *,
        organization,
    ):
        """
        Build organization-scoped approval intelligence.

        pending:
            ApprovalItems awaiting a final decision,
            including needs_info.

        approved:
            Explicitly approved ApprovalItems.

        rejected:
            Explicitly rejected ApprovalItems.

        Ignored approvals are intentionally excluded from
        these dashboard decision buckets.
        """

        queryset = (
            ApprovalItem.objects
            .filter(
                organization=organization,
            )
        )

        return {
            "pending": (
                queryset.filter(
                    status__in=self.PENDING_STATUSES,
                ).count()
            ),

            "approved": (
                queryset.filter(
                    status="approved",
                ).count()
            ),

            "rejected": (
                queryset.filter(
                    status="rejected",
                ).count()
            ),
        }
