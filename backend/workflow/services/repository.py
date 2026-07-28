from django.db import transaction

from workflow.models import (
    WorkflowDefinition,
    WorkflowNode,
    WorkflowTransition,
    WorkflowVariable,
)

from platform_core.observability import get_logger


logger = get_logger(__name__)

class WorkflowDefinitionRepository:

    @staticmethod
    def create(**kwargs):

        workflow = WorkflowDefinition.objects.create(
            **kwargs
        )

        logger.info(
            "WorkflowDefinition created (%s)",
            workflow.id,
        )

        return workflow

    @staticmethod
    def get(workflow_id):

        return WorkflowDefinition.objects.get(
            pk=workflow_id
        )

    @staticmethod
    def list(organization):

        return WorkflowDefinition.objects.filter(
            organization=organization
        ).order_by(
            "name",
            "-version",
        )

    @staticmethod
    def active(organization):

        return WorkflowDefinition.objects.filter(
            organization=organization,
            status=WorkflowDefinition.STATUS_ACTIVE,
        )

    @staticmethod
    def delete(workflow):

        workflow.delete()

class WorkflowNodeRepository:

    @staticmethod
    def create(**kwargs):

        node = WorkflowNode.objects.create(
            **kwargs
        )

        logger.info(
            "WorkflowNode created (%s)",
            node.id,
        )

        return node

    @staticmethod
    def workflow_nodes(workflow):

        return WorkflowNode.objects.filter(
            workflow=workflow
        )

    @staticmethod
    def get(node_id):

        return WorkflowNode.objects.get(
            pk=node_id
        )

class WorkflowTransitionRepository:

    @staticmethod
    def create(**kwargs):

        transition = WorkflowTransition.objects.create(
            **kwargs
        )

        logger.info(
            "WorkflowTransition created (%s)",
            transition.id,
        )

        return transition

    @staticmethod
    def workflow_transitions(workflow):

        return WorkflowTransition.objects.filter(
            workflow=workflow
        )

class WorkflowVariableRepository:

    @staticmethod
    def create(**kwargs):

        variable = WorkflowVariable.objects.create(
            **kwargs
        )

        logger.info(
            "WorkflowVariable created (%s)",
            variable.id,
        )

        return variable

    @staticmethod
    def workflow_variables(workflow):

        return WorkflowVariable.objects.filter(
            workflow=workflow
        )
    
class WorkflowRepository:

    definition = WorkflowDefinitionRepository

    node = WorkflowNodeRepository

    transition = WorkflowTransitionRepository

    variable = WorkflowVariableRepository