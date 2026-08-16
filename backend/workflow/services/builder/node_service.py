from workflow.models import WorkflowNode
from workflow.services.builder.repository import (
    WorkflowNodeRepository,
)

class WorkflowNodeService:

    def create_node(
        self,
        *,
        workflow,
        name,
        node_type,
        configuration=None,
        position_x=0,
        position_y=0,
    ):

        return WorkflowNodeRepository.create(
            workflow=workflow,
            name=name,
            node_type=node_type,
            configuration=configuration or {},
            position_x=position_x,
            position_y=position_y,
        )

    def update_position(
        self,
        node,
        *,
        x,
        y,
    ):

        node.position_x = x
        node.position_y = y

        WorkflowNodeRepository.save(node)

        return node