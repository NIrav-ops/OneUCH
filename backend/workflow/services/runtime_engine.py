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
        """

        if self.instance.status in [
            WorkflowInstance.STATUS_COMPLETED,
            WorkflowInstance.STATUS_FAILED,
            WorkflowInstance.STATUS_CANCELLED,
        ]:

            return self.instance

        self.controller.cancel()

        self.instance.status = (
            WorkflowInstance.STATUS_CANCELLED
        )

        self.instance.completed_at = timezone.now()

        self.instance.save(
            update_fields=[
                "status",
                "completed_at",
            ]
        )

        self._record_event(
            instance=self.instance,
            event=(
                WorkflowExecutionEventService
                .WORKFLOW_CANCELLED
            ),
            details={
                "reason": "Workflow execution cancelled.",
            },
        )

        return self.instance

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

                return transition.target

        #
        # Nothing matched.
        #

        if default_transition is not None:

            RoutingDiagnostics.default_transition(
                default_transition,
            )

            return default_transition.target

        RoutingDiagnostics.no_transition(
            node,
        )

        return None

    def execute_node(self, token):

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

        return (
            WorkflowRuntimeRepository.token.create(
                instance=self.instance,
                node=next_node,
            )
        )

    def _mark_failed(self):

        self.controller.fail()

        self.instance.status = (
            WorkflowInstance.STATUS_FAILED
        )

        self.instance.completed_at = (
            timezone.now()
        )

        self.instance.save(
            update_fields=[
                "status",
                "completed_at",
            ]
        )

    def _mark_completed(self):

        self.controller.complete()

        self.instance.status = (
            WorkflowInstance.STATUS_COMPLETED
        )

        self.instance.completed_at = (
            timezone.now()
        )

        self.instance.save(
            update_fields=[
                "status",
                "completed_at",
            ]
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

            self._record_event(
                instance=self.instance,
                event=(
                    WorkflowExecutionEventService
                    .WORKFLOW_COMPLETED
                ),
            )

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

        if self._get_waiting_tokens():

            raise ValueError(
                "Workflow is suspended and must be resumed."
            )

        #
        # A runtime that already contains execution tokens
        # has already started.
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

            self._record_event(
                event=(
                    WorkflowExecutionEventService
                    .WORKFLOW_STARTED
                ),
            )

            while current:

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

                self._record_event(
                    event=(
                        WorkflowExecutionEventService
                        .WORKFLOW_COMPLETED
                    ),
                )

                self._mark_completed()

            return self.instance

        except Exception as exc:

            failure_details = {
                "error_type": (
                    exc.__class__.__name__
                ),
                "error_message": str(exc),
            }

            #
            # Record node failure when a current token
            # exists.
            #

            if current is not None:

                self._record_event(
                    node=current.node,
                    event=(
                        WorkflowExecutionEventService
                        .NODE_FAILED
                    ),
                    details=failure_details,
                )

            #
            # Persist workflow failure.
            #

            self._mark_failed()

            #
            # Record workflow-level failure.
            #

            self._record_event(
                event=(
                    WorkflowExecutionEventService
                    .WORKFLOW_FAILED
                ),
                details=failure_details,
            )

            #
            # Preserve the original exception.
            #

            raise