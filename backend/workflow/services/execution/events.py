from workflow.services.runtime_repository import (
    WorkflowRuntimeRepository,
)


class WorkflowExecutionEventService:
    """
    Centralized service for recording workflow execution events.

    Execution history is an operational record of what happened
    during a workflow runtime.

    Runtime identity, workflow identity and correlation identity
    are always derived from the WorkflowInstance.

    Caller supplied metadata may add information, but must never
    replace authoritative runtime identity.

    Failure evidence is intentionally limited to operational
    classification metadata.

    Sensitive runtime payloads must never be persisted as
    execution-event details.
    """

    # ------------------------------------------------------------------
    # Workflow lifecycle events
    # ------------------------------------------------------------------

    WORKFLOW_CREATED = "workflow_created"
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    WORKFLOW_CANCELLED = "workflow_cancelled"

    # ------------------------------------------------------------------
    # Suspension / resume
    # ------------------------------------------------------------------

    WORKFLOW_SUSPENDED = "workflow_suspended"
    WORKFLOW_RESUMED = "workflow_resumed"

    # ------------------------------------------------------------------
    # Node lifecycle
    # ------------------------------------------------------------------

    NODE_STARTED = "node_started"
    NODE_COMPLETED = "node_completed"
    NODE_FAILED = "node_failed"

    # ------------------------------------------------------------------
    # Transition / routing
    # ------------------------------------------------------------------

    TRANSITION_SELECTED = "transition_selected"
    TRANSITION_REJECTED = "transition_rejected"

    # ------------------------------------------------------------------
    # Event taxonomy
    # ------------------------------------------------------------------

    WORKFLOW_EVENTS = {
        WORKFLOW_CREATED,
        WORKFLOW_STARTED,
        WORKFLOW_COMPLETED,
        WORKFLOW_FAILED,
        WORKFLOW_CANCELLED,
        WORKFLOW_SUSPENDED,
        WORKFLOW_RESUMED,
    }

    NODE_EVENTS = {
        NODE_STARTED,
        NODE_COMPLETED,
        NODE_FAILED,
    }

    ROUTING_EVENTS = {
        TRANSITION_SELECTED,
        TRANSITION_REJECTED,
    }

    ALL_EVENTS = (
        WORKFLOW_EVENTS
        | NODE_EVENTS
        | ROUTING_EVENTS
    )

    # ------------------------------------------------------------------
    # Event result classification
    # ------------------------------------------------------------------

    SUCCESS_EVENTS = {
        WORKFLOW_STARTED,
        WORKFLOW_COMPLETED,
        WORKFLOW_RESUMED,
        NODE_COMPLETED,
        TRANSITION_SELECTED,
    }

    FAILURE_EVENTS = {
        WORKFLOW_FAILED,
        NODE_FAILED,
        TRANSITION_REJECTED,
    }

    CONTROL_EVENTS = {
        WORKFLOW_CANCELLED,
        WORKFLOW_SUSPENDED,
    }

    # ------------------------------------------------------------------
    # Failure stages
    # ------------------------------------------------------------------

    FAILURE_STAGE_RUNTIME_INTEGRITY = (
        "runtime_integrity"
    )

    FAILURE_STAGE_NODE_EXECUTION = (
        "node_execution"
    )

    FAILURE_STAGE_ROUTING = (
        "routing"
    )

    FAILURE_STAGE_RUNTIME = (
        "runtime"
    )

    # ------------------------------------------------------------------
    # Failure types
    # ------------------------------------------------------------------

    FAILURE_TYPE_RUNTIME_INTEGRITY = (
        "runtime_integrity_error"
    )

    FAILURE_TYPE_NODE_EXECUTION = (
        "node_execution_error"
    )

    FAILURE_TYPE_ROUTING = (
        "routing_error"
    )

    FAILURE_TYPE_RUNTIME = (
        "runtime_error"
    )

    # ------------------------------------------------------------------
    # Event classification
    # ------------------------------------------------------------------

    @classmethod
    def get_category(
        cls,
        event,
    ):
        """
        Return the canonical operational category for an event.
        """

        if event in cls.WORKFLOW_EVENTS:
            return "workflow"

        if event in cls.NODE_EVENTS:
            return "node"

        if event in cls.ROUTING_EVENTS:
            return "routing"

        return "unknown"

    @classmethod
    def get_result(
        cls,
        event,
    ):
        """
        Return the operational result classification.

        This is derived from the canonical event type and cannot
        be trusted from caller supplied details.
        """

        if event in cls.SUCCESS_EVENTS:
            return "success"

        if event in cls.FAILURE_EVENTS:
            return "failure"

        if event in cls.CONTROL_EVENTS:
            return "control"

        return "unknown"

    @classmethod
    def is_terminal(
        cls,
        event,
    ):
        """
        Determine whether the event represents a terminal
        workflow lifecycle state.
        """

        return event in {
            cls.WORKFLOW_COMPLETED,
            cls.WORKFLOW_FAILED,
            cls.WORKFLOW_CANCELLED,
        }

    # ------------------------------------------------------------------
    # Failure classification
    # ------------------------------------------------------------------

    @classmethod
    def classify_failure(
        cls,
        *,
        exception,
        event,
    ):
        """
        Build canonical failure metadata.

        Raw exception messages are intentionally excluded.

        The exception type is retained because it provides useful
        operational evidence without persisting the exception
        payload itself.
        """

        error_type = (
            exception.__class__.__name__
        )

        if event == cls.NODE_FAILED:

            return {
                "failure_type": (
                    cls.FAILURE_TYPE_NODE_EXECUTION
                ),
                "failure_stage": (
                    cls.FAILURE_STAGE_NODE_EXECUTION
                ),
                "exception_type": error_type,
                "error_type": error_type,
            }

        if event == cls.WORKFLOW_FAILED:

            return {
                "failure_type": (
                    cls.FAILURE_TYPE_RUNTIME
                ),
                "failure_stage": (
                    cls.FAILURE_STAGE_RUNTIME
                ),
                "exception_type": error_type,
                "error_type": error_type,
            }

        if event == cls.TRANSITION_REJECTED:

            return {
                "failure_type": (
                    cls.FAILURE_TYPE_ROUTING
                ),
                "failure_stage": (
                    cls.FAILURE_STAGE_ROUTING
                ),
                "exception_type": error_type,
                "error_type": error_type,
            }

        raise ValueError(
            "Unsupported failure event."
        )

    @classmethod
    def sanitize_error_message(
        cls,
        message,
    ):
        """
        Sanitize an operational error message before it is
        exposed through workflow execution evidence.

        Security-sensitive credentials must never be persisted
        or returned in execution-history failure metadata.

        The sanitizer intentionally preserves ordinary
        operational error text because that information is useful
        for debugging and audit purposes.
        """

        if message is None:
            return None

        text = str(message)

        #
        # Authorization header / authorization token.
        #
        # Examples:
        #
        # Authorization token SECRET-TOKEN-123
        # Authorization: Bearer abc123
        # authorization=abc123
        #

        import re

        text = re.sub(
            r"(?i)"
            r"(authorization"
            r"(?:\s+token)?"
            r"\s*[:=]?\s+)"
            r"[^\s,;]+",
            r"\1[REDACTED]",
            text,
        )

        #
        # Bearer tokens.
        #
        # Examples:
        #
        # Bearer eyJhbGciOi...
        # bearer abcdef123
        #

        text = re.sub(
            r"(?i)"
            r"\bBearer\s+"
            r"[A-Za-z0-9._~+/=-]+",
            "Bearer [REDACTED]",
            text,
        )

        #
        # API keys.
        #
        # Examples:
        #
        # api_key=abc123
        # api-key: abc123
        # apikey abc123
        #

        text = re.sub(
            r"(?i)"
            r"\bapi[\s_-]?key"
            r"(\s*[:=]\s*|\s+)"
            r"[^\s,;]+",
            r"api_key\1[REDACTED]",
            text,
        )

        #
        # Common secret/token/password assignments.
        #
        # Keep this deliberately limited to credential-like
        # fields so ordinary operational messages remain intact.
        #

        text = re.sub(
            r"(?i)"
            r"\b(?:access[_ -]?token|refresh[_ -]?token|"
            r"client[_ -]?secret|secret|password)"
            r"(\s*[:=]\s*|\s+)"
            r"[^\s,;]+",
            lambda match: (
                f"{match.group(0)[:match.start(0) - match.start(0)]}"
            ),
            text,
        )

        #
        # The generic credential pattern above should not alter
        # ordinary text accidentally. Apply explicit replacements
        # instead for the supported credential fields.
        #

        text = re.sub(
            r"(?i)"
            r"\b(access[_ -]?token|refresh[_ -]?token|"
            r"client[_ -]?secret|password)"
            r"(\s*[:=]\s*|\s+)"
            r"[^\s,;]+",
            r"\1\2[REDACTED]",
            text,
        )

        return text

    # ------------------------------------------------------------------
    # Failure evidence
    # ------------------------------------------------------------------

    @classmethod
    def record_failure(
        cls,
        *,
        instance,
        event,
        exception,
        node=None,
        details=None,
        actor=None,
        actor_type=None,
        source=None,
    ):
        """
        Record a canonical failure event.

        Only safe operational failure classification is persisted.

        Raw exception messages, tracebacks, credentials, tokens,
        API keys and similar sensitive values are never persisted.
        """

        if event not in cls.FAILURE_EVENTS:

            raise ValueError(
                "Failure event required."
            )

        payload = dict(
            details or {}
        )

        #
        # Caller supplied failure evidence can never inject raw
        # exception content into the audit record.
        #

        payload.pop(
            "error_message",
            None,
        )

        payload.pop(
            "exception_message",
            None,
        )

        payload.pop(
            "traceback",
            None,
        )

        #
        # Canonical failure classification is authoritative.
        #

        payload.update(
            cls.classify_failure(
                exception=exception,
                event=event,
            )
        )

        #
        # Defensive cleanup.
        #

        payload.pop(
            "error_message",
            None,
        )

        payload.pop(
            "exception_message",
            None,
        )

        payload.pop(
            "traceback",
            None,
        )

        return cls.record(
            instance=instance,
            event=event,
            node=node,
            details=payload,
            actor=actor,
            actor_type=actor_type,
            source=source,
        )

    # ------------------------------------------------------------------
    # General event recording
    # ------------------------------------------------------------------

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

        Authoritative identity fields are always derived from
        WorkflowInstance and cannot be overridden by callers.
        """

        if event not in cls.ALL_EVENTS:

            raise ValueError(
                f"Unsupported workflow execution event: "
                f"{event}"
            )

        payload = dict(
            details or {}
        )

        # --------------------------------------------------------------
        # Authoritative execution identity
        # --------------------------------------------------------------

        payload["correlation_id"] = str(
            instance.pk
        )

        # --------------------------------------------------------------
        # Canonical event semantics
        # --------------------------------------------------------------

        payload["event_category"] = (
            cls.get_category(event)
        )

        payload["event_result"] = (
            cls.get_result(event)
        )

        payload["event_terminal"] = (
            cls.is_terminal(event)
        )

        # --------------------------------------------------------------
        # Workflow identity
        # --------------------------------------------------------------

        workflow = getattr(
            instance,
            "workflow",
            None,
        )

        if workflow is not None:

            payload["workflow_version"] = (
                workflow.version
            )

            payload["workflow_id"] = str(
                workflow.pk
            )

            payload["workflow_code"] = (
                workflow.code
            )

        # --------------------------------------------------------------
        # Execution initiator
        # --------------------------------------------------------------

        started_by = getattr(
            instance,
            "started_by",
            None,
        )

        if started_by is not None:

            payload["started_by"] = str(
                started_by.pk
            )

            payload["started_by_email"] = (
                getattr(
                    started_by,
                    "email",
                    None,
                )
            )

        else:

            payload["started_by"] = None
            payload["started_by_email"] = None

        # --------------------------------------------------------------
        # Runtime actor
        # --------------------------------------------------------------

        if actor is not None:

            payload["actor_id"] = str(
                actor.pk
            )

            payload["actor_email"] = (
                getattr(
                    actor,
                    "email",
                    None,
                )
            )

        elif "actor_id" not in payload:

            payload["actor_id"] = None

        if actor_type is not None:

            payload["actor_type"] = actor_type

        elif "actor_type" not in payload:

            payload["actor_type"] = None

        if source is not None:

            payload["source"] = source

        elif "source" not in payload:

            payload["source"] = None

        # --------------------------------------------------------------
        # Persist through the append-only repository.
        # --------------------------------------------------------------

        return WorkflowRuntimeRepository.log.create(
            instance=instance,
            node=node,
            event=event,
            details=payload,
        )