from workflow.services.execution_integrity import (
    WorkflowExecutionEventIntegrityError,
    WorkflowExecutionEventIntegrityService,
)

from workflow.models import (
    WorkflowExecutionLog,
)


class WorkflowExecutionHistoryIntegrityService:
    """
    Verifies the complete cryptographic integrity chain for one
    workflow execution instance.
    """

    @classmethod
    def verify_instance(
        cls,
        instance,
    ):
        events = list(
            WorkflowExecutionLog.objects
            .filter(
                instance=instance,
            )
            .order_by(
                "sequence_number",
                "created_at",
                "id",
            )
        )

        previous_hash = None
        expected_sequence = 1

        for event in events:

            if (
                event.sequence_number
                != expected_sequence
            ):

                raise WorkflowExecutionEventIntegrityError(
                    "Execution history sequence is invalid."
                )

            if (
                event.previous_event_hash
                != previous_hash
            ):

                raise WorkflowExecutionEventIntegrityError(
                    "Execution history chain is broken."
                )

            (
                WorkflowExecutionEventIntegrityService
                .verify_event(event)
            )

            previous_hash = event.event_hash

            expected_sequence += 1

        return {
            "valid": True,
            "event_count": len(events),
            "last_event_hash": previous_hash,
        }