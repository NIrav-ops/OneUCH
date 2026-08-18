import hashlib
import json


class WorkflowExecutionEventIntegrityError(
    ValueError
):
    """
    Raised when execution-event integrity validation fails.
    """

    pass


class WorkflowExecutionEventIntegrityService:
    """
    Provides canonical hashing and verification for workflow
    execution history.

    This module intentionally lives outside the execution package
    to avoid circular dependencies between the runtime repository
    and WorkflowExecutionEventService.
    """

    HASH_ALGORITHM = "sha256"

    @classmethod
    def _canonical_payload(
        cls,
        *,
        instance_id,
        sequence_number,
        previous_event_hash,
        event,
        node_id,
        details,
    ):
        """
        Build the deterministic representation used for hashing.
        """

        payload = {
            "instance_id": str(
                instance_id
            ),
            "sequence_number": (
                sequence_number
            ),
            "previous_event_hash": (
                previous_event_hash
            ),
            "event": event,
            "node_id": (
                str(node_id)
                if node_id is not None
                else None
            ),
            "details": details or {},
        }

        return json.dumps(
            payload,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
            ensure_ascii=False,
        ).encode(
            "utf-8"
        )

    @classmethod
    def calculate_hash(
        cls,
        *,
        instance_id,
        sequence_number,
        previous_event_hash,
        event,
        node_id,
        details,
    ):
        """
        Calculate the SHA-256 digest for one execution event.
        """

        canonical_payload = (
            cls._canonical_payload(
                instance_id=instance_id,
                sequence_number=sequence_number,
                previous_event_hash=(
                    previous_event_hash
                ),
                event=event,
                node_id=node_id,
                details=details,
            )
        )

        return hashlib.sha256(
            canonical_payload
        ).hexdigest()

    @classmethod
    def calculate_event_hash(
        cls,
        event,
    ):
        """
        Calculate the expected hash for an already persisted
        WorkflowExecutionLog instance.
        """

        return cls.calculate_hash(
            instance_id=event.instance_id,
            sequence_number=(
                event.sequence_number
            ),
            previous_event_hash=(
                event.previous_event_hash
            ),
            event=event.event,
            node_id=event.node_id,
            details=event.details,
        )

    @classmethod
    def verify_event(
        cls,
        event,
    ):
        """
        Verify one persisted execution event.
        """

        if event.sequence_number is None:

            raise WorkflowExecutionEventIntegrityError(
                "Execution event has no sequence number."
            )

        if event.event_hash is None:

            raise WorkflowExecutionEventIntegrityError(
                "Execution event has no event hash."
            )

        expected_hash = (
            cls.calculate_event_hash(
                event
            )
        )

        if event.event_hash != expected_hash:

            raise WorkflowExecutionEventIntegrityError(
                "Execution event hash is invalid."
            )

        return True