from workflow.models import (
    WorkflowDefinition,
    WorkflowNode,
    WorkflowTransition,
)


class WorkflowValidationError(Exception):
    """
    Raised when a workflow fails validation.
    """
    pass

class WorkflowValidator:
        @staticmethod
        def validate_definition(workflow: WorkflowDefinition):

            if not workflow.name.strip():
                raise WorkflowValidationError(
                    "Workflow name is required."
                )

            if not workflow.code.strip():
                raise WorkflowValidationError(
                    "Workflow code is required."
                )

            return True
        
        @staticmethod
        def validate_node(node: WorkflowNode):

            if not node.name.strip():
                raise WorkflowValidationError(
                    "Node name is required."
                )

            if node.node_type not in dict(
                WorkflowNode.NODE_TYPES
            ):
                raise WorkflowValidationError(
                    "Invalid node type."
                )

            return True
        

        @staticmethod
        def validate_transition(
            transition: WorkflowTransition,
        ):

            if transition.source == transition.target:
                raise WorkflowValidationError(
                    "Transition cannot point to itself."
                )

            if transition.source.workflow != transition.workflow:
                raise WorkflowValidationError(
                    "Source node belongs to another workflow."
                )

            if transition.target.workflow != transition.workflow:
                raise WorkflowValidationError(
                    "Target node belongs to another workflow."
                )

            return True

        @staticmethod
        def validate_workflow(workflow):

            WorkflowValidator.validate_definition(
                workflow
            )

            nodes = list(
                workflow.nodes.all()
            )

            transitions = list(
                workflow.transitions.all()
            )

            starts = [
                node
                for node in nodes
                if node.node_type == WorkflowNode.START
            ]

            if len(starts) != 1:

                raise WorkflowValidationError(
                    "Workflow must contain exactly one Start node."
                )

            ends = [
                node
                for node in nodes
                if node.node_type == WorkflowNode.END
            ]

            if len(ends) < 1:

                raise WorkflowValidationError(
                    "Workflow must contain at least one End node."
                )

            #
            # Validate every persisted node.
            #

            for node in nodes:

                WorkflowValidator.validate_node(
                    node
                )

            #
            # Validate every persisted transition.
            #

            for transition in transitions:

                WorkflowValidator.validate_transition(
                    transition
                )

            

            #
            # Build adjacency map.
            #
            # This uses persisted node IDs, not names.
            #

            adjacency = {
                node.pk: []
                for node in nodes
            }

            for transition in transitions:

                adjacency[
                    transition.source_id
                ].append(
                    transition.target_id
                )

            #
            # Traverse the graph from START.
            #

            reachable = set()

            stack = [
                starts[0].pk
            ]

            while stack:

                node_id = stack.pop()

                if node_id in reachable:
                    continue

                reachable.add(
                    node_id
                )

                for target_id in adjacency.get(
                    node_id,
                    [],
                ):

                    if target_id not in reachable:

                        stack.append(
                            target_id
                        )

            #
            # Every persisted node must be reachable
            # from START.
            #

            unreachable_nodes = [
                node
                for node in nodes
                if node.pk not in reachable
            ]

            if unreachable_nodes:

                names = ", ".join(
                    node.name
                    for node in unreachable_nodes
                )

                raise WorkflowValidationError(
                    "Workflow contains unreachable nodes: "
                    f"{names}."
                )

    #
    # Every END node must be reachable.
    #
    # This is technically covered by the previous
    # check, but keeping the explicit rule makes the
    # enterprise validation contract clear.
    #

            unreachable_ends = [
                node
                for node in ends
                if node.pk not in reachable
            ]

            if unreachable_ends:

                names = ", ".join(
                    node.name
                    for node in unreachable_ends
                )

                raise WorkflowValidationError(
                    "Workflow contains unreachable End nodes: "
                    f"{names}."
                )

            #
            # Execution-safety validation.
            #
            # At this point graph reachability has already
            # been validated.
            #
            # Therefore these checks validate execution
            # semantics rather than basic connectivity.
            #

            for node in nodes:

                incoming = [
                    transition
                    for transition in transitions
                    if transition.target_id == node.pk
                ]

                outgoing = [
                    transition
                    for transition in transitions
                    if transition.source_id == node.pk
                ]

                #
                # START is the workflow entry point.
                #

                if node.node_type == WorkflowNode.START:

                    if incoming:

                        raise WorkflowValidationError(
                            "START node cannot have incoming transitions."
                        )

                #
                # END terminates workflow execution.
                #

                if node.node_type == WorkflowNode.END:

                    if outgoing:

                        raise WorkflowValidationError(
                            "END node cannot have outgoing transitions."
                        )

                #
                # Every reachable non-END node must have
                # a continuation.
                #

                if node.node_type != WorkflowNode.END:

                    if not outgoing:

                        raise WorkflowValidationError(
                            f"Node '{node.name}' has no outgoing transition."
                        )

            return True