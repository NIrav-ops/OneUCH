from workflow.models import (
    WorkflowInstance,
    WorkflowToken,
)


class WorkflowRuntimeIntegrityError(
    ValueError
):
    """
    Raised when a workflow runtime instance violates
    execution-state integrity rules.
    """

    pass


class WorkflowRuntimeIntegrityService:
    """
    Validates invariants across WorkflowInstance,
    WorkflowToken and WorkflowNode.

    This is intentionally kept separate from the runtime
    execution engine so that integrity rules are centralized
    and independently testable.
    """

    TERMINAL_INSTANCE_STATUSES = {
        WorkflowInstance.STATUS_COMPLETED,
        WorkflowInstance.STATUS_FAILED,
        WorkflowInstance.STATUS_CANCELLED,
    }

    @classmethod
    def validate_instance(
        cls,
        instance,
    ):
        """
        Validate the complete runtime integrity boundary
        for one workflow instance.

        Returns True when the instance is internally
        consistent.

        Raises WorkflowRuntimeIntegrityError otherwise.
        """

        if instance.workflow_id is None:
            raise WorkflowRuntimeIntegrityError(
                "Workflow instance is not associated "
                "with a workflow definition."
            )

        if instance.organization_id != (
            instance.workflow.organization_id
        ):
            raise WorkflowRuntimeIntegrityError(
                "Workflow instance organization does not "
                "match its workflow organization."
            )

        tokens = (
            WorkflowToken.objects
            .filter(
                instance=instance,
            )
            .select_related(
                "node",
                "node__workflow",
            )
        )

        for token in tokens:
            cls.validate_token(
                token
            )

        if instance.status in (
            cls.TERMINAL_INSTANCE_STATUSES
        ):
            active_tokens = [
                token
                for token in tokens
                if token.status == (
                    WorkflowToken.STATUS_ACTIVE
                )
            ]

            if active_tokens:
                raise WorkflowRuntimeIntegrityError(
                    "Terminal workflow instance cannot "
                    "contain active execution tokens."
                )

        return True

    @classmethod
    def validate_token(
        cls,
        token,
    ):
        """
        Validate one runtime token against its instance
        and workflow node.
        """

        if token.instance_id is None:
            raise WorkflowRuntimeIntegrityError(
                "Workflow token is not associated "
                "with a runtime instance."
            )

        if token.node_id is None:
            raise WorkflowRuntimeIntegrityError(
                "Workflow token is not associated "
                "with a workflow node."
            )

        instance = token.instance
        node = token.node

        if node.workflow_id != instance.workflow_id:
            raise WorkflowRuntimeIntegrityError(
                "Workflow token node does not belong "
                "to the workflow being executed."
            )

        if node.workflow.organization_id != (
            instance.organization_id
        ):
            raise WorkflowRuntimeIntegrityError(
                "Workflow token crosses an organization "
                "boundary."
            )

        if token.status == (
            WorkflowToken.STATUS_WAITING
        ):
            if (
                token.wait_until is None
                and not token.wait_reason
            ):
                raise WorkflowRuntimeIntegrityError(
                    "Waiting workflow token must contain "
                    "wait state information."
                )

        if token.status == (
            WorkflowToken.STATUS_COMPLETED
        ):
            if token.completed_at is None:
                raise WorkflowRuntimeIntegrityError(
                    "Completed workflow token must contain "
                    "a completion timestamp."
                )

        return True