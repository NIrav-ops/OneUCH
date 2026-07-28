import logging

from actions.services.repository import ActionRepository

logger = logging.getLogger(__name__)


class ActionIntegrationService:
    """
    Workflow → Actions integration layer.

    The workflow engine should only communicate with this service,
    never directly with ActionItem or ActionRepository.
    """

    @classmethod
    def create_action(cls, **payload):

        payload.setdefault(
            "source_type",
            "workflow",
        )

        action = ActionRepository.create_action(
            **payload,
        )

        logger.info(
            "Workflow created ActionItem (%s)",
            action.pk,
        )

        return action