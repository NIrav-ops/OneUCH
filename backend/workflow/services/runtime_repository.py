from django.db import transaction

from workflow.models import (
    WorkflowInstance,
    WorkflowToken,
    WorkflowExecutionLog,
    WorkflowDefinition,
)

from platform_core.observability import get_logger

from workflow.services.execution_integrity import (
    WorkflowExecutionEventIntegrityService,
)

logger = get_logger(__name__)

class WorkflowInstanceRepository:

    @staticmethod
    @transaction.atomic
    def create(**kwargs):

        instance = WorkflowInstance.objects.create(
            **kwargs
        )

        logger.info(
            "WorkflowInstance created (%s)",
            instance.id,
        )

        return instance

    @staticmethod
    def get(instance_id):

        return WorkflowInstance.objects.get(
            id=instance_id
        )

    @staticmethod
    def running():

        return WorkflowInstance.objects.filter(
            status=WorkflowInstance.STATUS_RUNNING
        )

    @staticmethod
    def by_workflow(workflow):

        return WorkflowInstance.objects.filter(
            workflow=workflow
        )

    @staticmethod
    def save(instance):

        instance.save()

        return instance
    
class WorkflowTokenRepository:

    @staticmethod
    @transaction.atomic
    def create(**kwargs):

        token = WorkflowToken.objects.create(
            **kwargs
        )

        logger.info(
            "WorkflowToken created (%s)",
            token.id,
        )

        return token

    @staticmethod
    def active(instance):

        return WorkflowToken.objects.filter(
            instance=instance,
            status=WorkflowToken.STATUS_ACTIVE,
        )

    @staticmethod
    def by_node(node):

        return WorkflowToken.objects.filter(
            node=node
        )

    @staticmethod
    def save(token):

        token.save()

        return token

    @staticmethod
    def active_by_node(instance, node):

        return WorkflowToken.objects.filter(
            instance=instance,
            node=node,
            status=WorkflowToken.STATUS_ACTIVE,
        )

class WorkflowExecutionLogRepository:

    @staticmethod
    @transaction.atomic
    def create(**kwargs):

        #
        # Extract authoritative fields from kwargs.
        #
        # These fields are controlled by the repository and
        # must never be passed through a second time via **kwargs.
        #

        instance = kwargs.pop(
            "instance"
        )

        node = kwargs.pop(
            "node",
            None,
        )

        event = kwargs.pop(
            "event"
        )

        details = kwargs.pop(
            "details",
            None,
        )

        #
        # Integrity fields are repository-owned.
        #
        # A caller may supply these values, but they are ignored.
        # This prevents forged sequence numbers, previous hashes,
        # and event hashes.
        #

        kwargs.pop(
            "sequence_number",
            None,
        )

        kwargs.pop(
            "previous_event_hash",
            None,
        )

        kwargs.pop(
            "event_hash",
            None,
        )

        #
        # Resolve the previous event in this execution.
        #
        # The execution history is an append-only chain.
        #

        previous_event = (
            WorkflowExecutionLog.objects
            .filter(
                instance=instance,
            )
            .order_by(
                "-sequence_number",
                "-created_at",
                "-id",
            )
            .first()
        )

        if previous_event is None:

            sequence_number = 1
            previous_event_hash = None

        else:

            sequence_number = (
                previous_event.sequence_number
                + 1
            )

            previous_event_hash = (
                previous_event.event_hash
            )

        #
        # Calculate the authoritative event hash.
        #

        event_hash = (
            WorkflowExecutionEventIntegrityService
            .calculate_hash(
                instance_id=instance.pk,
                sequence_number=sequence_number,
                previous_event_hash=(
                    previous_event_hash
                ),
                event=event,
                node_id=(
                    node.pk
                    if node is not None
                    else None
                ),
                details=details or {},
            )
        )

        #
        # Only non-integrity metadata may pass through.
        #

        log = WorkflowExecutionLog.objects.create(
            instance=instance,
            node=node,
            event=event,
            details=details or {},
            sequence_number=sequence_number,
            previous_event_hash=(
                previous_event_hash
            ),
            event_hash=event_hash,
            **kwargs,
        )

        logger.info(
            "WorkflowExecutionLog created (%s)",
            log.id,
        )

        return log

    @staticmethod
    def update(
        *args,
        **kwargs,
    ):

        raise PermissionError(
            "Workflow execution history is append-only "
            "and cannot be updated."
        )

    @staticmethod
    def delete(
        *args,
        **kwargs,
    ):

        raise PermissionError(
            "Workflow execution history is append-only "
            "and cannot be deleted."
        )

    @staticmethod
    def instance_logs(
        instance,
    ):

        return (
            WorkflowExecutionLog.objects
            .filter(
                instance=instance,
            )
        )

    @staticmethod
    def for_instance(
        instance,
    ):

        return (
            WorkflowExecutionLog.objects
            .filter(
                instance=instance,
            )
            .select_related(
                "node",
            )
            .order_by(
                "sequence_number",
                "created_at",
                "id",
            )
        )
class WorkflowRuntimeRepository:

    instance = WorkflowInstanceRepository
    token = WorkflowTokenRepository
    log = WorkflowExecutionLogRepository