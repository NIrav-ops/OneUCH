from workflow.models import WorkflowNode


class WorkflowGraphValidator:

    """
    Validates the structure of a workflow graph before
    persistence.

    This validator validates the graph payload only.

    It does NOT validate whether the workflow is ready
    to be published.

    Publish-time validation is handled by WorkflowValidator.
    """

    def validate(
        self,
        graph,
    ):

        if not isinstance(
            graph,
            dict,
        ):

            raise ValueError(
                "Graph must be an object."
            )

        if "nodes" not in graph:

            raise ValueError(
                "Graph must contain nodes."
            )

        if not isinstance(
            graph["nodes"],
            list,
        ):

            raise ValueError(
                "Graph nodes must be a list."
            )

        if not graph["nodes"]:

            raise ValueError(
                "Workflow must contain at least one node."
            )

        if "transitions" not in graph:

            raise ValueError(
                "Graph must contain transitions."
            )

        if not isinstance(
            graph["transitions"],
            list,
        ):

            raise ValueError(
                "Graph transitions must be a list."
            )

        valid_node_types = {
            value
            for value, _ in WorkflowNode.NODE_TYPES
        }

        client_ids = set()

        #
        # Validate nodes
        #

        for node in graph["nodes"]:

            if not isinstance(
                node,
                dict,
            ):

                raise ValueError(
                    "Each workflow node must be an object."
                )

            client_id = node.get(
                "client_id"
            )

            if not client_id:

                raise ValueError(
                    "Every workflow node requires client_id."
                )

            if client_id in client_ids:

                raise ValueError(
                    f"Duplicate node client_id '{client_id}'."
                )

            client_ids.add(
                client_id
            )

            if not node.get(
                "name"
            ):

                raise ValueError(
                    "Every workflow node requires name."
                )

            node_type = node.get(
                "node_type"
            )

            if node_type not in valid_node_types:

                raise ValueError(
                    f"Invalid workflow node type '{node_type}'."
                )

        #
        # Validate transitions
        #

        for transition in graph["transitions"]:

            if not isinstance(
                transition,
                dict,
            ):

                raise ValueError(
                    "Each workflow transition must be an object."
                )

            source = transition.get(
                "source"
            )

            target = transition.get(
                "target"
            )

            if not source:

                raise ValueError(
                    "Every transition requires source."
                )

            if not target:

                raise ValueError(
                    "Every transition requires target."
                )

            if source not in client_ids:

                raise ValueError(
                    f"Transition source '{source}' does not exist."
                )

            if target not in client_ids:

                raise ValueError(
                    f"Transition target '{target}' does not exist."
                )

        return True