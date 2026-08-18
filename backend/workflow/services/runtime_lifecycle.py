from django.db import transaction
from django.utils import timezone

from workflow.models import WorkflowInstance

from workflow.services.execution import (
    WorkflowExecutionEventService,
)


class WorkflowRuntimeLifecycleError(
    ValueError
):
    """
    Raised when a workflow runtime lifecycle transition
    is invalid.
    """

    pass


class WorkflowRuntimeLifecycleService:
    """
    Owns authoritative WorkflowInstance lifecycle transitions.

    This service deliberately keeps lifecycle state changes and
    their corresponding execution events inside the same database
    transaction.

    It does NOT execute workflow nodes and does NOT decide routing.

    Its responsibility is limited to maintaining the invariant:

        runtime state transition
            +
        corresponding audit event

    must succeed or fail together.
    """

    TERMINAL_STATUSES = {
        WorkflowInstance.STATUS_COMPLETED,
        WorkflowInstance.STATUS_FAILED,
        WorkflowInstance.STATUS_CANCELLED,
    }

    @classmethod
    def _ensure_running(
        cls,
        instance,
    ):
        if (
            instance.status
            != WorkflowInstance.STATUS_RUNNING
        ):
            raise WorkflowRuntimeLifecycleError(
                "Only running workflow instances "
                "can transition to another lifecycle state."
            )

    @classmethod
    @transaction.atomic
    def cancel(
        cls,
        instance,
        *,
        actor=None,
        actor_type=None,
        source=None,
        reason="Workflow execution cancelled.",
    ):
        """
        Transition a running workflow to CANCELLED.

        Cancellation is idempotent at the runtime API level:
        an already-cancelled instance is returned unchanged.

        Other terminal states are immutable.
        """

        if (
            instance.status
            == WorkflowInstance.STATUS_CANCELLED
        ):
            return instance

        if (
            instance.status
            in {
                WorkflowInstance.STATUS_COMPLETED,
                WorkflowInstance.STATUS_FAILED,
            }
        ):
            return instance

        cls._ensure_running(
            instance
        )

        instance.status = (
            WorkflowInstance.STATUS_CANCELLED
        )

        instance.completed_at = timezone.now()

        instance.save(
            update_fields=[
                "status",
                "completed_at",
            ]
        )

        WorkflowExecutionEventService.record(
            instance=instance,
            event=(
                WorkflowExecutionEventService
                .WORKFLOW_CANCELLED
            ),
            details={
                "reason": reason,
            },
            actor=actor,
            actor_type=actor_type,
            source=source,
        )

        return instance

    @classmethod
    @transaction.atomic
    def complete(
        cls,
        instance,
        *,
        actor=None,
        actor_type=None,
        source=None,
    ):
        """
        Transition a running workflow to COMPLETED.

        Terminal completion is immutable and idempotent.
        """

        if (
            instance.status
            == WorkflowInstance.STATUS_COMPLETED
        ):
            return instance

        if (
            instance.status
            in {
                WorkflowInstance.STATUS_FAILED,
                WorkflowInstance.STATUS_CANCELLED,
            }
        ):
            return instance

        cls._ensure_running(
            instance
        )

        instance.status = (
            WorkflowInstance.STATUS_COMPLETED
        )

        instance.completed_at = timezone.now()

        instance.save(
            update_fields=[
                "status",
                "completed_at",
            ]
        )

        WorkflowExecutionEventService.record(
            instance=instance,
            event=(
                WorkflowExecutionEventService
                .WORKFLOW_COMPLETED
            ),
            actor=actor,
            actor_type=actor_type,
            source=source,
        )

        return instance

    @classmethod
    @transaction.atomic
    def fail(
        cls,
        instance,
        *,
        error_type,
        error_message,
        actor=None,
        actor_type=None,
        source=None,
    ):
        """
        Transition a running workflow to FAILED.

        The failure metadata is persisted together with the
        workflow-level failure event.

        Terminal failures are immutable and idempotent.
        """

        if (
            instance.status
            == WorkflowInstance.STATUS_FAILED
        ):
            return instance

        if (
            instance.status
            in {
                WorkflowInstance.STATUS_COMPLETED,
                WorkflowInstance.STATUS_CANCELLED,
            }
        ):
            return instance

        cls._ensure_running(
            instance
        )

        failure_details = {
            "error_type": error_type,
            "error_message": error_message,
        }

        instance.status = (
            WorkflowInstance.STATUS_FAILED
        )

        instance.completed_at = timezone.now()

        instance.save(
            update_fields=[
                "status",
                "completed_at",
            ]
        )

        WorkflowExecutionEventService.record(
            instance=instance,
            event=(
                WorkflowExecutionEventService
                .WORKFLOW_FAILED
            ),
            details=failure_details,
            actor=actor,
            actor_type=actor_type,
            source=source,
        )

        return instance