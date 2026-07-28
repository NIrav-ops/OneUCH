from platform_core.events.publisher import (
    EventPublisher,
)

from platform_core.events.factory import (
    EventFactory,
)

from platform_core.events.names import (
    WORKFLOW_COMPLETED,
)


class WorkflowEventPublisher:

    def completed(
        self,
        workflow_id,
    ):

        EventPublisher().publish(

            EventFactory.create(

                name=WORKFLOW_COMPLETED,

                payload={

                    "workflow_id": workflow_id,

                },

            )

        )