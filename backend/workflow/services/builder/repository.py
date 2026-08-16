from django.db import transaction

from workflow.models import (
    WorkflowDefinition,
    WorkflowNode,
    WorkflowTransition,
)


class WorkflowDefinitionRepository:

    @staticmethod
    @transaction.atomic
    def create(**kwargs):

        return WorkflowDefinition.objects.create(
            **kwargs
        )

    @staticmethod
    def all():

        return WorkflowDefinition.objects.all()

    @staticmethod
    def get(workflow_id):

        return WorkflowDefinition.objects.get(
            pk=workflow_id
        )

    @staticmethod
    def by_organization(
        organization,
    ):

        return WorkflowDefinition.objects.filter(
            organization=organization
        )

    @staticmethod
    def save(
        workflow,
    ):

        workflow.save()

        return workflow

    @staticmethod
    @transaction.atomic
    def delete(
        workflow,
    ):

        workflow.delete()

    @staticmethod
    def versions(
        *,
        organization,
        code,
    ):

        return WorkflowDefinition.objects.filter(
            organization=organization,
            code=code,
        ).order_by(
            "-version",
            "-id",
        )

    @staticmethod
    def latest_version(
        *,
        organization,
        code,
    ):

        return (
            WorkflowDefinition.objects.filter(
                organization=organization,
                code=code,
            )
            .order_by(
                "-version",
                "-id",
            )
            .first()
        )

    @staticmethod
    def deactivate_other_versions(
        *,
        organization,
        code,
        exclude_workflow,
    ):

        return (
            WorkflowDefinition.objects
            .filter(
                organization=organization,
                code=code,
                status=(
                    WorkflowDefinition.STATUS_ACTIVE
                ),
            )
            .exclude(
                pk=exclude_workflow.pk,
            )
            .update(
                status=WorkflowDefinition.STATUS_ARCHIVED,
            )
        )


class WorkflowBuilderRepository:

    """
    Repository responsible only for workflow graph
    persistence.

    No business lifecycle logic belongs here.
    """

    @staticmethod
    def workflow(pk):

        return WorkflowDefinition.objects.get(
            pk=pk,
        )

    @staticmethod
    def create_workflow(
        **kwargs,
    ):

        return WorkflowDefinition.objects.create(
            **kwargs,
        )

    @staticmethod
    def save_workflow(
        workflow,
    ):

        workflow.save()

        return workflow

    @staticmethod
    def delete_nodes(
        workflow,
    ):

        WorkflowNode.objects.filter(
            workflow=workflow,
        ).delete()

    @staticmethod
    def delete_transitions(
        workflow,
    ):

        WorkflowTransition.objects.filter(
            workflow=workflow,
        ).delete()

    @staticmethod
    def create_node(
        **kwargs,
    ):

        return WorkflowNode.objects.create(
            **kwargs,
        )

    @staticmethod
    def create_transition(
        **kwargs,
    ):

        return WorkflowTransition.objects.create(
            **kwargs,
        )

    @staticmethod
    @transaction.atomic
    def replace_graph(
        workflow,
        *,
        nodes,
        transitions,
    ):

        WorkflowTransition.objects.filter(
            workflow=workflow,
        ).delete()

        WorkflowNode.objects.filter(
            workflow=workflow,
        ).delete()

        created = {}

        for node in nodes:

            created[
                node["client_id"]
            ] = WorkflowNode.objects.create(
                workflow=workflow,
                name=node["name"],
                node_type=node["node_type"],
                configuration=node.get(
                    "configuration",
                    {},
                ),
                position_x=node.get(
                    "position_x",
                    node.get("x", 0),
                ),
                position_y=node.get(
                    "position_y",
                    node.get("y", 0),
                ),
            )

        for transition in transitions:

            WorkflowTransition.objects.create(
                workflow=workflow,
                source_node=created[
                    transition["source"]
                ],
                target_node=created[
                    transition["target"]
                ],
                condition=transition.get(
                    "condition",
                    "",
                ),
                priority=transition.get(
                    "priority",
                    100,
                ),
            )

        return workflow


class WorkflowNodeRepository:

    @staticmethod
    def create(**kwargs):

        return WorkflowNode.objects.create(
            **kwargs
        )

    @staticmethod
    def save(
        node,
    ):

        node.save()

        return node

    @staticmethod
    def delete_by_workflow(
        workflow,
    ):

        return WorkflowNode.objects.filter(
            workflow=workflow,
        ).delete()


class WorkflowTransitionRepository:

    @staticmethod
    def create(**kwargs):

        return WorkflowTransition.objects.create(
            **kwargs
        )

    @staticmethod
    def save(
        transition,
    ):

        transition.save()

        return transition

    @staticmethod
    def delete_by_workflow(
        workflow,
    ):

        return WorkflowTransition.objects.filter(
            workflow=workflow,
        ).delete()