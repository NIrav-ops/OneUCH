from workflow.services.runtime_repository import (
    WorkflowRuntimeRepository,
)


class WorkflowExecutionEventService:
    """
    Centralized service for recording workflow execution events.

    All runtime execution events should pass through this service.

    The service is intentionally independent of HTTP/API request
    context. Runtime identity is derived from WorkflowInstance,
    while optional actor/source metadata can be supplied by callers.

    Workflow version information is always derived from the workflow
    attached to the WorkflowInstance so that execution history remains
    pinned to the exact workflow definition used by the runtime.
    """

    # ------------------------------------------------------------------
    # Node events
    # ------------------------------------------------------------------

    NODE_STARTED = "node_started"
    NODE_COMPLETED = "node_completed"
    NODE_FAILED = "node_failed"

    # ------------------------------------------------------------------
    # Workflow lifecycle events
    # ------------------------------------------------------------------

    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    WORKFLOW_CANCELLED = "workflow_cancelled"

    # ------------------------------------------------------------------
    # Suspension / resume events
    # ------------------------------------------------------------------

    WORKFLOW_SUSPENDED = "workflow_suspended"
    WORKFLOW_RESUMED = "workflow_resumed"

    @classmethod
    def record(
        cls,
        *,
        instance,
        event,
        node=None,
        details=None,
        actor=None,
        actor_type=None,
        source=None,
    ):
        """
        Record one workflow execution event.

        Parameters
        ----------
        instance:
            WorkflowInstance associated with the runtime execution.

        event:
            Event name, normally one of the constants defined on this
            service.

        node:
            Optional WorkflowNode associated with the event.

        details:
            Optional event-specific metadata dictionary.

        actor:
            Optional authenticated/user actor responsible for the
            operation. This is separate from WorkflowInstance.started_by.

        actor_type:
            Optional actor classification such as "user", "system",
            "service", etc.

        source:
            Optional source such as "runtime_api", "scheduler",
            "webhook", "system", etc.

        Returns
        -------
        WorkflowExecutionLog
            The persisted execution log record.
        """

        # --------------------------------------------------------------
        # Start with caller supplied details.
        # --------------------------------------------------------------

        payload = dict(
            details or {}
        )

        # --------------------------------------------------------------
        # Execution correlation
        #
        # WorkflowInstance is the authoritative execution identity.
        #
        # A caller must never be able to override the correlation
        # identifier because that would allow audit events to appear
        # associated with another execution.
        # --------------------------------------------------------------

        payload["correlation_id"] = str(
            instance.pk
        )

        # --------------------------------------------------------------
        # Workflow identity
        #
        # Always derive these values from the WorkflowInstance.
        # Callers must not be able to accidentally associate an event
        # with another workflow version.
        # --------------------------------------------------------------

        workflow = getattr(
            instance,
            "workflow",
            None,
        )

        if workflow is not None:

            payload.setdefault(
                "workflow_version",
                workflow.version,
            )

            payload.setdefault(
                "workflow_id",
                str(
                    workflow.pk
                ),
            )

            payload.setdefault(
                "workflow_code",
                workflow.code,
            )

        # --------------------------------------------------------------
        # Execution initiator
        #
        # WorkflowInstance.started_by may be NULL for system initiated
        # executions such as scheduled workflows, webhooks, integrations,
        # or future event-triggered executions.
        # --------------------------------------------------------------

        started_by = getattr(
            instance,
            "started_by",
            None,
        )

        if started_by is not None:

            payload.setdefault(
                "started_by",
                str(
                    started_by.pk
                ),
            )

            payload.setdefault(
                "started_by_email",
                getattr(
                    started_by,
                    "email",
                    None,
                ),
            )

        else:

            payload.setdefault(
                "started_by",
                None,
            )

            payload.setdefault(
                "started_by_email",
                None,
            )

        # --------------------------------------------------------------
        # Optional runtime actor metadata
        #
        # These fields are intentionally retained because existing
        # runtime code already passes actor / actor_type / source.
        # --------------------------------------------------------------

        if actor is not None:

            payload.setdefault(
                "actor_id",
                str(
                    actor.pk
                ),
            )

            payload.setdefault(
                "actor_email",
                getattr(
                    actor,
                    "email",
                    None,
                ),
            )

        elif "actor_id" not in payload:

            payload["actor_id"] = None

        if actor_type is not None:

            payload.setdefault(
                "actor_type",
                actor_type,
            )

        elif "actor_type" not in payload:

            payload["actor_type"] = None

        if source is not None:

            payload.setdefault(
                "source",
                source,
            )

        elif "source" not in payload:

            payload["source"] = None

        # --------------------------------------------------------------
        # Persist the event through the runtime repository.
        # --------------------------------------------------------------

        return WorkflowRuntimeRepository.log.create(
            instance=instance,
            node=node,
            event=event,
            details=payload,
        )