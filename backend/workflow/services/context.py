from copy import deepcopy

from workflow.models import WorkflowInstance

class WorkflowExecutionContext:

    """
    Runtime execution context.

    Holds all variables for one workflow execution.
    """

    def __init__(self, instance: WorkflowInstance):

        self.instance = instance

        self._variables = deepcopy(
            instance.context or {}
        )
    
    def get(
        self,
        key,
        default=None,
    ):

        return self._variables.get(
            key,
            default,
        )
    
    def set(
        self,
        key,
        value,
    ):

        self._variables[key] = value
    
    def update(
        self,
        values: dict,
    ):

        self._variables.update(
            values
        )
    
    def exists(
        self,
        key,
    ):

        return key in self._variables
    
    def remove(
        self,
        key,
    ):

        if key in self._variables:

            del self._variables[key]

    def suspend(
        self,
        reason,
        metadata=None,
    ):
        """
        Mark the current workflow execution context as suspended.

        Suspension is a runtime state, not an execution failure.

        Examples:
        - AI human review
        - external approval
        - timer/wait node
        - asynchronous external dependency
        """

        self.set(
            "workflow_suspended",
            True,
        )

        self.set(
            "suspension_reason",
            reason,
        )

        self.set(
            "suspension_metadata",
            metadata or {},
        )

    def resume(self):
        """
        Clear runtime suspension state.

        Actual token reactivation is controlled by the
        workflow execution engine.
        """

        self.set(
            "workflow_suspended",
            False,
        )

        self.set(
            "suspension_reason",
            None,
        )

        self.set(
            "suspension_metadata",
            {},
        )

    def set_review_resolution(
        self,
        resolution,
    ):
        """
        Store the resolved human-review outcome.

        The workflow engine may later inspect this record
        to determine whether execution may safely continue.
        """

        if hasattr(
            resolution,
            "review_id",
        ):
            payload = {
                "review_id": resolution.review_id,
                "approved": resolution.approved,
                "rejected": resolution.rejected,
                "can_continue": resolution.can_continue,
                "reviewer": resolution.reviewer,
                "comments": resolution.comments,
                "reason": resolution.reason,
            }
        else:
            payload = dict(resolution)

        self.set(
            "ai_review_resolution",
            payload,
        )


    @property
    def review_resolution(
        self,
    ):
        return self.get(
            "ai_review_resolution"
        )


    @property
    def review_completed(
        self,
    ):
        return (
            self.review_resolution
            is not None
        )


    @property
    def review_approved(
        self,
    ):
        resolution = (
            self.review_resolution
            or {}
        )

        return bool(
            resolution.get(
                "approved",
                False,
            )
        )


    @property
    def review_rejected(
        self,
    ):
        resolution = (
            self.review_resolution
            or {}
        )

        return bool(
            resolution.get(
                "rejected",
                False,
            )
        )    

    def clear_pending_review(
        self,
    ):
        """
        Remove transient review-request state after
        a human decision has been recorded.
        """

        self.set(
            "ai_pending_review",
            None,
        )

        self.set(
            "ai_pending_reviews",
            [],
        )

        self.set(
            "ai_review_pending",
            False,
        )

    @property
    def is_suspended(self):

        return bool(
            self.get(
                "workflow_suspended",
                False,
            )
        )        

    def serialize(self):

        return deepcopy(
            self._variables
        )
    
    def save(self):

        self.instance.context = self.serialize()

        self.instance.save(
            update_fields=[
                "context",
            ]
        )

        return self.instance