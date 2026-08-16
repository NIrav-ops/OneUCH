from django.db import transaction

from workflow.models import (
    WorkflowInstance,
    WorkflowToken,
    WorkflowExecutionLog,
    WorkflowDefinition,
)

from platform_core.observability import get_logger

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

        log = WorkflowExecutionLog.objects.create(
            **kwargs
        )

        logger.info(
            "WorkflowExecutionLog created (%s)",
            log.id,
        )

        return log

    @staticmethod
    def instance_logs(instance):

        return WorkflowExecutionLog.objects.filter(
            instance=instance
        )

    @staticmethod
    def for_instance(instance):
        return WorkflowExecutionLog.objects.filter(
            instance=instance,
        ).select_related(
            "node",
        ).order_by(
            "created_at",
        )
class WorkflowRuntimeRepository:

    instance = WorkflowInstanceRepository
    token = WorkflowTokenRepository
    log = WorkflowExecutionLogRepository