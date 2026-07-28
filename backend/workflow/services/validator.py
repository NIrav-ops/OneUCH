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

            nodes = workflow.nodes.all()

            transitions = workflow.transitions.all()
            
            starts = [
                n for n in nodes
                if n.node_type == WorkflowNode.START
            ]

            if len(starts) != 1:
                raise WorkflowValidationError(
                    "Workflow must contain exactly one Start node."
                )

            ends = [
                n for n in nodes
                if n.node_type == WorkflowNode.END
            ]

            if len(ends) < 1:
                raise WorkflowValidationError(
                    "Workflow must contain at least one End node."
                )

            for node in nodes:
                WorkflowValidator.validate_node(
                    node
                )
            
            for transition in transitions:
                WorkflowValidator.validate_transition(
                    transition
                )

            return True    
            