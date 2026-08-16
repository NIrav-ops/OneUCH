import logging

logger = logging.getLogger(__name__)


class RoutingDiagnostics:

    @classmethod
    def transition_selected(
        cls,
        transition,
        variables,
    ):
        logger.debug(
            "Workflow routing selected transition %s "
            "condition=%s variables=%s",
            transition.id,
            transition.condition,
            variables,
        )

    @classmethod
    def default_transition(
        cls,
        transition,
    ):
        logger.debug(
            "Workflow routing default transition %s",
            transition.id,
        )

    @classmethod
    def no_transition(
        cls,
        node,
    ):
        logger.warning(
            "Workflow node %s has no valid outgoing transition.",
            node.id,
        )