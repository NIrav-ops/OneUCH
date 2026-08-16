from django.db import transaction

from workflow.services.builder.workflow_service import (
    WorkflowBuilderService,
)

from workflow.services.builder.node_service import (
    WorkflowNodeService,
)

from workflow.services.builder.transition_service import (
    WorkflowTransitionService,
)

from workflow.services.builder.graph_validator import (
    WorkflowGraphValidator,
)

from workflow.services.builder.repository import (
    WorkflowDefinitionRepository,
    WorkflowNodeRepository,
    WorkflowTransitionRepository,
)

from workflow.serializers.workflow_graph import (
    WorkflowGraphResponseSerializer,
)


class WorkflowGraphService:
    """
    Coordinates complete workflow graph persistence.

    Responsibilities:

    - validate graph payload
    - enforce draft-only editing
    - replace existing nodes/transitions
    - map frontend client IDs to database IDs
    - serialize persisted graphs back to the frontend
    - persist atomically

    Publish-time validation remains the responsibility of
    WorkflowBuilderService.
    """

    def __init__(self):

        self.workflow_service = (
            WorkflowBuilderService()
        )

        self.node_service = (
            WorkflowNodeService()
        )

        self.transition_service = (
            WorkflowTransitionService()
        )

        self.validator = (
            WorkflowGraphValidator()
        )

    def _ensure_editable(
        self,
        workflow,
    ):
        """
        Only draft workflow definitions may be edited.

        Published versions are immutable because runtime
        instances are pinned to an exact WorkflowDefinition.
        """

        if (
            workflow.status
            != workflow.STATUS_DRAFT
        ):

            raise ValueError(
                "Only draft workflows can be edited."
            )

    @transaction.atomic
    def save_graph(
        self,
        *,
        workflow,
        graph,
    ):
        """
        Replace the complete graph for a draft workflow.

        The operation is atomic. If any node or transition
        fails to persist, the complete graph change rolls back.
        """

        self._ensure_editable(
            workflow
        )

        self.validator.validate(
            graph
        )

        WorkflowTransitionRepository.delete_by_workflow(
            workflow
        )

        WorkflowNodeRepository.delete_by_workflow(
            workflow
        )

        created_nodes = {}

        node_mapping = {}

        for node in graph["nodes"]:

            created = (
                self.node_service.create_node(

                    workflow=workflow,

                    name=node["name"],

                    node_type=node["node_type"],

                    configuration=node.get(
                        "configuration",
                        {},
                    ),

                    position_x=node.get(
                        "position_x",
                        0,
                    ),

                    position_y=node.get(
                        "position_y",
                        0,
                    ),
                )
            )

            client_id = node[
                "client_id"
            ]

            created_nodes[
                client_id
            ] = created

            node_mapping[
                client_id
            ] = str(
                created.pk
            )

        for transition in graph[
            "transitions"
        ]:

            self.transition_service.create_transition(

                workflow=workflow,

                source=created_nodes[
                    transition["source"]
                ],

                target=created_nodes[
                    transition["target"]
                ],

                priority=transition.get(
                    "priority",
                    100,
                ),

                condition=transition.get(
                    "condition",
                    "",
                ),
            )

        WorkflowDefinitionRepository.save(
            workflow
        )

        return {
            "workflow_id": str(
                workflow.pk
            ),
            "nodes": node_mapping,
        }

    def get_graph(
        self,
        *,
        workflow,
    ):
        """
        Return the persisted workflow graph in the same
        client-ID based format expected by the frontend.
        """

        nodes = list(
            workflow.nodes.all().order_by(
                "created_at",
                "id",
            )
        )

        node_client_ids = {
            str(node.pk): str(node.pk)
            for node in nodes
        }

        serialized_nodes = []

        for node in nodes:

            client_id = node_client_ids[
                str(node.pk)
            ]

            serialized_nodes.append(
                {
                    "id": str(
                        node.pk
                    ),

                    "client_id": client_id,

                    "name": node.name,

                    "node_type": node.node_type,

                    "configuration": (
                        node.configuration or {}
                    ),

                    "position_x": node.position_x,

                    "position_y": node.position_y,
                }
            )

        serialized_transitions = []

        transitions = (
            workflow.transitions.all()
            .select_related(
                "source",
                "target",
            )
            .order_by(
                "priority",
                "id",
            )
        )

        for transition in transitions:

            serialized_transitions.append(
                {
                    "id": str(
                        transition.pk
                    ),

                    "source": node_client_ids[
                        str(
                            transition.source_id
                        )
                    ],

                    "target": node_client_ids[
                        str(
                            transition.target_id
                        )
                    ],

                    "priority": (
                        transition.priority
                    ),

                    "condition": (
                        transition.condition or ""
                    ),
                }
            )

        result = {
            "workflow": workflow.pk,

            "workflow_code": workflow.code,

            "workflow_name": workflow.name,

            "workflow_version": workflow.version,

            "workflow_status": workflow.status,

            "editable": (
                workflow.status
                == workflow.STATUS_DRAFT
            ),

            "nodes": serialized_nodes,

            "transitions": serialized_transitions,
        }

        serializer = WorkflowGraphResponseSerializer(
            result
        )

        return serializer.data