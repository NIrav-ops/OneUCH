from copy import deepcopy

from django.db import transaction

from workflow.models import (
    WorkflowDefinition,
    WorkflowNode,
    WorkflowTransition,
)

from workflow.services.validation.validator import (
    WorkflowValidator,
)

from workflow.services.builder.repository import (
    WorkflowDefinitionRepository,
)


class WorkflowBuilderService:
    """
    Application service responsible for creating,
    reading, updating, deleting and publishing
    workflow definitions.

    Business rules belong here.

    Persistence belongs to the repository.
    """

    def create_workflow(
        self,
        *,
        organization,
        name,
        code,
        description="",
        created_by=None,
    ):

        return WorkflowDefinitionRepository.create(
            organization=organization,
            name=name,
            code=code,
            description=description,
            created_by=created_by,
        )

    def list_workflows(
        self,
        *,
        organization=None,
    ):

        if organization is None:

            return WorkflowDefinitionRepository.all()

        return (
            WorkflowDefinitionRepository
            .by_organization(
                organization
            )
        )

    def get_workflow(
        self,
        workflow_id,
    ):

        return WorkflowDefinitionRepository.get(
            workflow_id
        )

    def update_workflow(
        self,
        workflow,
        **fields,
    ):

        #
        # Active and archived workflow definitions
        # are immutable.
        #

        if workflow.status == (
            WorkflowDefinition.STATUS_ACTIVE
        ):

            raise ValueError(
                "Active workflows cannot be modified."
            )

        if workflow.status == (
            WorkflowDefinition.STATUS_ARCHIVED
        ):

            raise ValueError(
                "Archived workflows cannot be modified."
            )

        #
        # Only editable definition fields are allowed.
        #

        allowed_fields = {
            "name",
            "code",
            "description",
        }

        for field, value in fields.items():

            if field not in allowed_fields:

                raise ValueError(
                    f"Unsupported workflow field: "
                    f"'{field}'."
                )

            setattr(
                workflow,
                field,
                value,
            )

        return WorkflowDefinitionRepository.save(
            workflow
        )

    def delete_workflow(
        self,
        workflow,
    ):

        #
        # Published workflow definitions must not
        # be deleted in place.
        #

        if workflow.status == (
            WorkflowDefinition.STATUS_ACTIVE
        ):

            raise ValueError(
                "Active workflows cannot be deleted."
            )

        if workflow.status == (
            WorkflowDefinition.STATUS_ARCHIVED
        ):

            raise ValueError(
                "Archived workflows cannot be deleted."
            )

        return WorkflowDefinitionRepository.delete(
            workflow
        )

    def validate(
        self,
        workflow,
    ):

        WorkflowValidator().validate(
            workflow
        )

        return workflow

    @transaction.atomic
    def publish(
        self,
        workflow,
    ):
        """
        Publish a draft workflow version.

        Only draft workflows can be published.

        Publishing one version automatically retires any
        currently active version of the same workflow code
        within the same organization.
        """

        if workflow.status == (
            WorkflowDefinition.STATUS_ACTIVE
        ):

            raise ValueError(
                "Workflow is already active."
            )

        if workflow.status != (
            WorkflowDefinition.STATUS_DRAFT
        ):

            raise ValueError(
                "Only draft workflows can be published."
            )

        self.validate(
            workflow
        )

        (
            WorkflowDefinitionRepository
            .deactivate_other_versions(
                organization=workflow.organization,
                code=workflow.code,
                exclude_workflow=workflow,
            )
        )

        workflow.status = (
            WorkflowDefinition.STATUS_ACTIVE
        )

        WorkflowDefinitionRepository.save(
            workflow
        )

        return workflow

    @transaction.atomic
    def create_new_version(
        self,
        workflow,
    ):
        """
        Create a new draft version from an existing
        workflow definition.

        The source workflow is never modified.
        """

        if workflow.status != (
            WorkflowDefinition.STATUS_ACTIVE
        ):

            raise ValueError(
                "Only active workflows can create a new version."
            )

        latest = (
            WorkflowDefinitionRepository
            .latest_version(
                organization=workflow.organization,
                code=workflow.code,
            )
        )

        next_version = (
            (latest.version + 1)
            if latest is not None
            else 1
        )

        new_workflow = (
            WorkflowDefinitionRepository.create(
                organization=workflow.organization,
                name=workflow.name,
                code=workflow.code,
                description=workflow.description,
                version=next_version,
                status=(
                    WorkflowDefinition.STATUS_DRAFT
                ),
                created_by=workflow.created_by,
            )
        )

        #
        # Copy nodes first because transitions reference
        # the newly created nodes.
        #

        node_map = {}

        source_nodes = (
            WorkflowNode.objects.filter(
                workflow=workflow
            ).order_by("id")
        )

        for source_node in source_nodes:

            new_node = WorkflowNode.objects.create(
                workflow=new_workflow,
                name=source_node.name,
                node_type=source_node.node_type,
                configuration=(
                    deepcopy(
                        source_node.configuration
                        or {}
                    )
                ),
                position_x=source_node.position_x,
                position_y=source_node.position_y,
            )

            node_map[
                source_node.pk
            ] = new_node

        #
        # Copy transitions and reconnect them to the
        # newly created nodes.
        #

        source_transitions = (
            WorkflowTransition.objects.filter(
                workflow=workflow
            ).order_by("id")
        )

        for source_transition in source_transitions:

            WorkflowTransition.objects.create(
                workflow=new_workflow,
                source=node_map[
                    source_transition.source_id
                ],
                target=node_map[
                    source_transition.target_id
                ],
                condition=deepcopy(
                    source_transition.condition
                ),
                priority=source_transition.priority,
            )

        return new_workflow