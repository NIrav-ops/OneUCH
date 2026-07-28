import logging

from approvals.services.repository import ApprovalRepository

logger = logging.getLogger(__name__)


class ApprovalIntegrationService:
    """
    Workflow → Approvals integration layer.
    """

    @classmethod
    def create_request(cls, **payload):

        payload.setdefault(
            "source_type",
            "workflow",
        )

        approval = ApprovalRepository.create_request(
            **payload,
        )

        logger.info(
            "Workflow created ApprovalItem (%s)",
            approval.pk,
        )

        return approval