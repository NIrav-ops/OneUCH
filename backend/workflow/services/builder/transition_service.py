from workflow.models import WorkflowTransition
from workflow.services.builder.repository import (
    WorkflowTransitionRepository,
)


class WorkflowTransitionService:

    def create_transition(
        self,
        *,
        workflow,
        source,
        target,
        priority=100,
        condition="",
    ):

        return WorkflowTransitionRepository.create(
            workflow=workflow,
            source=source,
            target=target,
            priority=priority,
            condition=condition,
        )