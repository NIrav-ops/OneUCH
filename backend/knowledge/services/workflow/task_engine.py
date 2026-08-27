from django.utils import timezone

from actions.models import ActionItem

from knowledge.services.workflow.base_workflow_engine import (
    BaseWorkflowEngine,
)


class TaskEngine(
    BaseWorkflowEngine,
):

    category = "tasks"

    ACTIVE_STATUSES = (
        "open",
        "in_progress",
        "waiting",
        "blocked",
    )

    def build(
        self,
        *,
        organization,
    ):
        """
        Build organization-scoped task intelligence.

        Semantics:

        total:
            Every ActionItem belonging to the organization.

        pending:
            Active execution states only.

        completed:
            Explicitly completed ActionItems only.

        overdue:
            Active ActionItems with a due date earlier than now.

        Cancelled and ignored items remain part of historical
        total but are not treated as pending, completed, or overdue.
        """

        queryset = (
            ActionItem.objects
            .filter(
                organization=organization,
            )
        )

        pending_queryset = (
            queryset.filter(
                status__in=self.ACTIVE_STATUSES,
            )
        )

        return {
            "total": queryset.count(),

            "pending": (
                pending_queryset.count()
            ),

            "completed": (
                queryset.filter(
                    status="completed",
                ).count()
            ),

            "overdue": (
                pending_queryset.filter(
                    due_date__isnull=False,
                    due_date__lt=timezone.now(),
                ).count()
            ),
        }
