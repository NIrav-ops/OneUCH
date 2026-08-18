from django.utils import timezone

from workflow.models import (
    WorkflowInstance,
    WorkflowNode,
    WorkflowToken,
)

from workflow.services.context import (
    WorkflowExecutionContext,
)

from workflow.services.executors import (
    ExecutorFactory,
)

from workflow.services.runtime_repository import (
    WorkflowRuntimeRepository,
)

from workflow.services.execution import (
    WorkflowExecutionEventService,
)

from workflow.services.runtime_controller import (
    RuntimeController,
)

from workflow.services.routing import RoutingEvaluator

from workflow.services.routing.diagnostics import (
    RoutingDiagnostics,
)

from workflow.services.runtime_lifecycle import (
    WorkflowRuntimeLifecycleService,
)

from workflow.services.runtime_integrity import (
    WorkflowRuntimeIntegrityError,
    WorkflowRuntimeIntegrityService,
)

class WorkflowRuntimeEngine:
    """
    Enterprise workflow runtime engine.

    Responsible for orchestrating workflow execution.

    Responsibilities:
    - create runtime tokens
    - dispatch node executors
    - advance workflow tokens
    - stop execution when runtime becomes suspended
    - maintain runtime controller state
    - persist workflow failure state

    This engine intentionally does NOT:
    - execute AI directly
    - resolve approvals
    - resume suspended workflows
    """

    def __init__(
        self,
        instance,
        *,
        actor=None,
        actor_type=None,
        source=None,
    ):

        self.instance = instance

        self.actor = actor
        self.actor_type = actor_type
        self.source = source

        #
        # WorkflowInstance.workflow is the authoritative
        # runtime definition/version pin.
        #
        self.workflow = instance.workflow

        self.context = WorkflowExecutionContext(
            instance
        )

        #
        # RuntimeController owns the in-memory
        # execution lifecycle state.
        #
        self.controller = RuntimeController()

    def _validate_runtime_integrity(self):
        """
        Validate the persisted runtime execution boundary.

        Runtime integrity is enforced inside the execution engine
        rather than only at the API layer so that every execution
        entry point receives the same protection.
        """

        return (
            WorkflowRuntimeIntegrityService
            .validate_instance(
                self.instance
            )
        )

    def _is_terminal(self):
        return self.instance.status in {
            WorkflowInstance.STATUS_COMPLETED,
            WorkflowInstance.STATUS_FAILED,
            WorkflowInstance.STATUS_CANCELLED,
        }

    def _get_active_tokens(self):
        return list(
            WorkflowToken.objects.filter(
                instance=self.instance,
                status=WorkflowToken.STATUS_ACTIVE,
            ).select_related("node")
        )

    def _get_waiting_tokens(self):
        return list(
            WorkflowToken.objects.filter(
                instance=self.instance,
                status=WorkflowToken.STATUS_WAITING,
            ).select_related("node")
        )

    def _has_started_execution(self):
        return WorkflowToken.objects.filter(
            instance=self.instance,
        ).exists()

    def _record_event(
        self,
        *,
        event,
        node=None,
        details=None,
        instance=None,
        actor=None,
        actor_type=None,
        source=None,
    ):
        """
        Record a runtime execution event.

        This method intentionally accepts optional instance/actor/source
        arguments for compatibility with existing runtime-engine call
        sites. The engine's instance and execution identity remain the
        defaults.
        """

        effective_instance = (
            instance
            if instance is not None
            else self.instance
        )

        effective_actor = (
            actor
            if actor is not None
            else self.actor
        )

        effective_actor_type = (
            actor_type
            if actor_type is not None
            else self.actor_type
        )

        effective_source = (
            source
            if source is not None
            else self.source
        )

        return WorkflowExecutionEventService.record(
            instance=effective_instance,
            event=event,
            node=node,
            details=details,
            actor=effective_actor,
            actor_type=effective_actor_type,
            source=effective_source,
        )

    def cancel(self):

        """
        Cancel the currently running workflow instance.

        Cancellation is an explicit runtime control operation.
        It does not alter the workflow definition.

        The pinned WorkflowDefinition/version remains unchanged.

        Runtime state and the cancellation audit event are
        committed atomically.
        """

        if self.instance.status in {
            WorkflowInstance.STATUS_COMPLETED,
            WorkflowInstance.STATUS_FAILED,
            WorkflowInstance.STATUS_CANCELLED,
        }:

            return self.instance

        self.controller.cancel()

        return (
            WorkflowRuntimeLifecycleService.cancel(
                self.instance,
                actor=self.actor,
                actor_type=self.actor_type,
                source=self.source,
            )
        )

    def get_start_node(self):

        start_nodes = list(
            WorkflowNode.objects.filter(
                workflow=self.instance.workflow,
                node_type=WorkflowNode.START,
            )
        )

        if not start_nodes:

            raise ValueError(
                "Workflow has no START node."
            )

        if len(start_nodes) > 1:

            raise ValueError(
                "Workflow has multiple START nodes."
            )

        return start_nodes[0]

    def get_next_node(
        self,
        node,
        runtime_context=None,
    ):
        """
        Returns the next workflow node based on
        transition conditions.

        If multiple transitions exist,
        the first matching transition wins.

        If no condition matches,
        an unconditional transition is used.

        Returns None when no valid
        transition exists.
        """

        transitions = list(
            node.outgoing.order_by(
                "priority",
                "id",
            )
        )

        if not transitions:

            RoutingDiagnostics.no_transition(
                node,
            )

            self._record_event(
                node=node,
                event=(
                    WorkflowExecutionEventService
                    .TRANSITION_REJECTED
                ),
                details={
                    "source_node_id": str(
                        node.pk
                    ),
                    "evaluation": (
                        "no_outgoing_transition"
                    ),
                },
            )

            return None

        variables = {}

        if runtime_context is not None:

            if hasattr(
                runtime_context,
                "variables",
            ):

                variables = (
                    runtime_context.variables
                    or {}
                )

        default_transition = None

        for transition in transitions:

            condition = (
                transition.condition or ""
            ).strip()

            #
            # Remember unconditional route.
            #

            if condition == "":

                if default_transition is None:

                    default_transition = (
                        transition
                    )

                continue

            #
            # Evaluate condition.
            #

            if RoutingEvaluator.evaluate(
                condition,
                variables,
            ):

                RoutingDiagnostics.transition_selected(
                    transition,
                    variables,
                )

                self._record_event(
                    node=node,
                    event=(
                        WorkflowExecutionEventService
                        .TRANSITION_SELECTED
                    ),
                    details={
                        "transition_id": str(
                            transition.pk
                        ),
                        "source_node_id": str(
                            node.pk
                        ),
                        "target_node_id": str(
                            transition.target_id
                        ),
                        "evaluation": (
                            "condition_matched"
                        ),
                    },
                )

                return transition.target

        #
        # Nothing matched.
        #

        if default_transition is not None:

            RoutingDiagnostics.default_transition(
                default_transition,
            )

            self._record_event(
                node=node,
                event=(
                    WorkflowExecutionEventService
                    .TRANSITION_SELECTED
                ),
                details={
                    "transition_id": str(
                        default_transition.pk
                    ),
                    "source_node_id": str(
                        node.pk
                    ),
                    "target_node_id": str(
                        default_transition.target_id
                    ),
                    "evaluation": (
                        "default_transition"
                    ),
                },
            )

            return default_transition.target

        RoutingDiagnostics.no_transition(
            node,
        )

        self._record_event(
            node=node,
            event=(
                WorkflowExecutionEventService
                .TRANSITION_REJECTED
            ),
            details={
                "source_node_id": str(
                    node.pk
                ),
                "evaluation": (
                    "no_transition_available"
                ),
            },
        )

        return None

    def execute_node(self, token):

        WorkflowRuntimeIntegrityService.validate_token(
            token
        )

        executor_cls = (
            ExecutorFactory.get_executor(
                token.node.node_type
            )
        )

        executor = executor_cls(
            self.context,
            token,
        )

        executor.execute()

        #
        # A suspended context means that this token
        # represents a node waiting for external input.
        #
        # Persist it as WAITING instead of COMPLETED.
        #

        if self.context.is_suspended:

            token.status = (
                WorkflowToken.STATUS_WAITING
            )

            WorkflowRuntimeRepository.token.save(
                token
            )

            self.context.save()

            return token

        #
        # Normal node completion.
        #

        token.status = (
            WorkflowToken.STATUS_COMPLETED
        )

        token.completed_at = timezone.now()

        WorkflowRuntimeRepository.token.save(
            token
        )

        self.context.save()

        return token

    def advance(self, token):

        WorkflowRuntimeIntegrityService.validate_token(
            token
        )

        if self.context.is_suspended:
            return None

        #
        # END is a legitimate terminal node.
        #

        if token.node.node_type == WorkflowNode.END:

            return None

        next_node = self.get_next_node(
            token.node,
            self.context,
        )

        #
        # Any non-END node without a valid transition
        # represents an invalid runtime graph.
        #

        if next_node is None:

            raise ValueError(
                "Workflow execution stopped because "
                f"node '{token.node.name}' has no valid "
                "outgoing transition."
            )

        next_token = (
            WorkflowRuntimeRepository.token.create(
                instance=self.instance,
                node=next_node,
            )
        )

        WorkflowRuntimeIntegrityService.validate_token(
            next_token
        )

        return next_token

    def _mark_failed(
        self,
        *,
        error_type,
        error_message,
    ):

        self.controller.fail()

        return (
            WorkflowRuntimeLifecycleService.fail(
                self.instance,
                error_type=error_type,
                error_message=error_message,
                actor=self.actor,
                actor_type=self.actor_type,
                source=self.source,
            )
        )

    def _mark_completed(self):

        self.controller.complete()

        return (
            WorkflowRuntimeLifecycleService.complete(
                self.instance,
                actor=self.actor,
                actor_type=self.actor_type,
                source=self.source,
            )
        )

    def resume(self):
        """
        Resume a suspended workflow instance.

        Resume always continues from the persisted WAITING
        token. It never creates a new START token and never
        resolves the workflow definition again.

        The WorkflowInstance.workflow foreign key therefore
        remains the authoritative workflow/version pin.
        """

        if (
            self.instance.status
            == WorkflowInstance.STATUS_COMPLETED
        ):

            raise ValueError(
                "Completed workflows cannot be resumed."
            )

        if (
            self.instance.status
            == WorkflowInstance.STATUS_FAILED
        ):

            raise ValueError(
                "Failed workflows cannot be resumed."
            )

        if (
            self.instance.status
            == WorkflowInstance.STATUS_CANCELLED
        ):

            raise ValueError(
                "Cancelled workflows cannot be resumed."
            )

        waiting_token = (
            WorkflowToken.objects
            .filter(
                instance=self.instance,
                status=WorkflowToken.STATUS_WAITING,
            )
            .order_by(
                "-entered_at"
            )
            .first()
        )

        if waiting_token is None:

            raise ValueError(
                "Workflow has no waiting token to resume."
            )

        #
        # A resume operation must never trust persisted
        # waiting state without validating it first.
        #

        self._validate_runtime_integrity()

        WorkflowRuntimeIntegrityService.validate_token(
            waiting_token
        )

        #
        # Clear persisted suspension state.
        #

        self.context.resume()

        self.context.save()

        #
        # The waiting node has already performed its
        # suspension-triggering work. It can now be
        # completed and execution can advance.
        #

        waiting_token.status = (
            WorkflowToken.STATUS_COMPLETED
        )

        waiting_token.completed_at = (
            timezone.now()
        )

        WorkflowRuntimeRepository.token.save(
            waiting_token
        )

        WorkflowRuntimeIntegrityService.validate_token(
            waiting_token
        )

        #
        # Restore runtime controller state.
        #

        self.controller.start()

        self._record_event(
            instance=self.instance,
            node=waiting_token.node,
            event=(
                WorkflowExecutionEventService
                .WORKFLOW_RESUMED
            ),
            details={
                "resumed_from_token": str(
                    waiting_token.pk
                ),
            },
        )

        #
        # Continue from the node that was waiting.
        #

        current = self.advance(
            waiting_token
        )

        while current:

            if self.context.is_suspended:

                self._record_event(
                    instance=self.instance,
                    node=current.node,
                    event=(
                        WorkflowExecutionEventService
                        .WORKFLOW_SUSPENDED
                    ),
                )

                self.controller.wait()

                break

            self._record_event(
                instance=self.instance,
                node=current.node,
                event=(
                    WorkflowExecutionEventService
                    .NODE_STARTED
                ),
            )

            self.execute_node(
                current
            )

            if self.context.is_suspended:

                self._record_event(
                    instance=self.instance,
                    node=current.node,
                    event=(
                        WorkflowExecutionEventService
                        .WORKFLOW_SUSPENDED
                    ),
                    details={
                        "reason": self.context.get(
                            "suspension_reason"
                        ),
                        "metadata": self.context.get(
                            "suspension_metadata",
                            {},
                        ),
                    },
                )

                self.controller.wait()

                break

            self._record_event(
                instance=self.instance,
                node=current.node,
                event=(
                    WorkflowExecutionEventService
                    .NODE_COMPLETED
                ),
            )

            current = self.advance(
                current
            )

        #
        # Resume may have reached the end of the workflow.
        #

        if not self.context.is_suspended:

            self._mark_completed()

        return self.instance    

    def run(self):

        #
        # Do not restart terminal workflow instances.
        #

        if self.instance.status == (
            WorkflowInstance.STATUS_CANCELLED
        ):

            return self.instance

        if self.instance.status == (
            WorkflowInstance.STATUS_COMPLETED
        ):

            return self.instance

        if self.instance.status == (
            WorkflowInstance.STATUS_FAILED
        ):

            return self.instance

        #
        # A runtime that already has a waiting token must
        # be resumed rather than started again.
        #
        # This is a lifecycle guard, not an integrity failure.
        #

        if self._get_waiting_tokens():

            raise ValueError(
                "Workflow is suspended and must be resumed."
            )

        #
        # Validate persisted runtime integrity BEFORE checking
        # whether execution has already started.
        #
        # An integrity violation is a genuine runtime failure
        # and must therefore transition the instance to FAILED.
        #

        try:

            self._validate_runtime_integrity()

        except WorkflowRuntimeIntegrityError as exc:

            self._mark_failed(
                error_type=(
                    exc.__class__.__name__
                ),
                error_message=str(exc),
            )

            raise

        #
        # A valid runtime that already contains execution
        # tokens has already started.
        #
        # This is intentionally outside the failure boundary.
        #
        # It must NOT transition the workflow to FAILED.
        #

        if self._has_started_execution():

            raise ValueError(
                "Workflow execution has already started."
            )

        #
        # Runtime controller enters RUNNING state only
        # after lifecycle guards have passed.
        #

        self.controller.start()

        current = None

        try:

            #
            # Resolve and create the START token inside
            # the protected execution boundary.
            #
            # This ensures invalid workflow definitions
            # are persisted as FAILED rather than being
            # left in RUNNING state.
            #

            start_node = self.get_start_node()

            current = (
                WorkflowRuntimeRepository.token.create(
                    instance=self.instance,
                    node=start_node,
                )
            )

            #
            # Validate the token immediately after persistence.
            #
            # This guarantees that the first execution token
            # also satisfies the runtime integrity boundary.
            #

            WorkflowRuntimeIntegrityService.validate_token(
                current
            )

            self._record_event(
                event=(
                    WorkflowExecutionEventService
                    .WORKFLOW_STARTED
                ),
            )

            while current:

                #
                # Validate the token before allowing the node
                # to execute.
                #
                # This prevents a corrupted or cross-workflow
                # token from entering the executor layer.
                #

                WorkflowRuntimeIntegrityService.validate_token(
                    current
                )

                #
                # A node may suspend the workflow.
                #

                if self.context.is_suspended:

                    self._record_event(
                        node=current.node,
                        event=(
                            WorkflowExecutionEventService
                            .WORKFLOW_SUSPENDED
                        ),
                        details={
                            "reason": self.context.get(
                                "suspension_reason"
                            ),
                            "metadata": self.context.get(
                                "suspension_metadata",
                                {},
                            ),
                        },
                    )

                    self.controller.wait()

                    return self.instance

                #
                # Node started.
                #

                self._record_event(
                    node=current.node,
                    event=(
                        WorkflowExecutionEventService
                        .NODE_STARTED
                    ),
                )

                #
                # Execute the node.
                #

                self.execute_node(
                    current
                )

                #
                # A suspended node is WAITING, not
                # completed.
                #

                if self.context.is_suspended:

                    self._record_event(
                        node=current.node,
                        event=(
                            WorkflowExecutionEventService
                            .WORKFLOW_SUSPENDED
                        ),
                        details={
                            "reason": self.context.get(
                                "suspension_reason"
                            ),
                            "metadata": self.context.get(
                                "suspension_metadata",
                                {},
                            ),
                        },
                    )

                    self.controller.wait()

                    return self.instance

                #
                # Only genuinely completed nodes receive
                # NODE_COMPLETED.
                #

                self._record_event(
                    node=current.node,
                    event=(
                        WorkflowExecutionEventService
                        .NODE_COMPLETED
                    ),
                )

                #
                # Advance to the next node.
                #

                current = self.advance(
                    current
                )

            #
            # The runtime reached a legitimate terminal
            # condition.
            #
            # advance() returns None for END nodes.
            #

            if not self.context.is_suspended:

                self._mark_completed()

            return self.instance

        except Exception as exc:

            #
            # Failure evidence must cross the execution-history
            # boundary through record_failure().
            #
            # This guarantees:
            #
            # - canonical failure classification
            # - canonical failure stage
            # - exception type
            # - no raw exception message
            # - no caller-controlled failure classification
            #
            # The exception itself remains in memory only so the
            # original runtime error can be re-raised.
            #

            if current is not None:

                WorkflowExecutionEventService.record_failure(
                    instance=self.instance,
                    node=current.node,
                    event=(
                        WorkflowExecutionEventService
                        .NODE_FAILED
                    ),
                    exception=exc,
                    actor=getattr(
                        self,
                        "actor",
                        None,
                    ),
                    actor_type=getattr(
                        self,
                        "actor_type",
                        None,
                    ),
                    source=getattr(
                        self,
                        "source",
                        None,
                    ),
                )

            #
            # Persist workflow failure state.
            #

            self._mark_failed(
                error_type=(
                    exc.__class__.__name__
                ),
                    error_message=str(exc),
            )

            #
            # Record canonical workflow-level failure evidence.
            #
            # record_failure() intentionally excludes the raw
            # exception message from execution history.
            #

            WorkflowExecutionEventService.record_failure(
                instance=self.instance,
                event=(
                    WorkflowExecutionEventService
                    .WORKFLOW_FAILED
                ),
                exception=exc,
                actor=getattr(
                    self,
                    "actor",
                    None,
                ),
                actor_type=getattr(
                    self,
                    "actor_type",
                    None,
                ),
                source=getattr(
                    self,
                    "source",
                    None,
                ),
            )

            #
            # Preserve the original exception for the caller.
            #

            raise