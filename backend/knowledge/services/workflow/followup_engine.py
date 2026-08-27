from actions.models import (
    ExpectedResponseItem,
    FollowUpItem,
)

from knowledge.services.workflow.base_workflow_engine import (
    BaseWorkflowEngine,
)


class FollowupEngine(
    BaseWorkflowEngine,
):

    category = "followups"

    def build(
        self,
        *,
        organization,
    ):
        """
        Build organization-scoped follow-up intelligence.

        required:
            Every detected explicit follow-up obligation
            plus every expected-response obligation.

        completed:
            Completed explicit follow-ups plus received
            expected responses.

        pending:
            Pending explicit follow-ups plus waiting
            expected responses.

        Ignored items remain part of historical required
        totals but are excluded from completed/pending.
        """

        followups = (
            FollowUpItem.objects
            .filter(
                organization=organization,
            )
        )

        expected_responses = (
            ExpectedResponseItem.objects
            .filter(
                organization=organization,
            )
        )

        required = (
            followups.count()
            + expected_responses.count()
        )

        completed = (
            followups.filter(
                status="completed",
            ).count()
            + expected_responses.filter(
                status="received",
            ).count()
        )

        pending = (
            followups.filter(
                status="pending",
            ).count()
            + expected_responses.filter(
                status="waiting",
            ).count()
        )

        return {
            "required": required,
            "completed": completed,
            "pending": pending,
        }
