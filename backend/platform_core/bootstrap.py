from platform_core.registry import (
    ServiceRegistry,
)

from platform_core.constants import *

from context.services.customer360 import (
    Customer360Service,
)

from knowledge.services.organization360 import (
    Organization360Service,
)

from knowledge.services.people360 import (
    People360Service,
)

from knowledge.services.communication_intelligence import (
    CommunicationIntelligenceService,
)

from knowledge.services.search_service import (
    SearchService,
)

from knowledge.services.ai.intelligence import (
    AIIntelligenceService,
)

from knowledge.services.risk.executive_risk import (
    ExecutiveRiskService,
)

from knowledge.services.opportunity.executive_opportunity import (
    ExecutiveOpportunityService,
)

from knowledge.services.workflow.intelligence import (
    WorkflowIntelligenceService,
)

from platform_core.events.registry import (
    EventRegistry,
)

from platform_core.events.subscription_manager import (
    SubscriptionManager,
)

from platform_core.events.subscribers import (
    LoggingSubscriber,
    WorkflowAuditSubscriber,
)

from platform_core.audit.subscriber import (
    AuditSubscriber,
)

from platform_core.notifications.subscriber import (
    KnowledgeNotificationSubscriber,
)


def bootstrap_events():
    """
    Initialize Enterprise Event Registry.
    """

    EventRegistry.clear()


def bootstrap():
    """
    Register all enterprise platform services.
    """

    ServiceRegistry.clear()

    ServiceRegistry.register(
        CUSTOMER360,
        Customer360Service(),
    )

    ServiceRegistry.register(
        ORGANIZATION360,
        Organization360Service(),
    )

    ServiceRegistry.register(
        PEOPLE360,
        People360Service(),
    )

    ServiceRegistry.register(
        COMMUNICATION,
        CommunicationIntelligenceService(),
    )

    ServiceRegistry.register(
        SEARCH,
        SearchService(),
    )

    ServiceRegistry.register(
        AI,
        AIIntelligenceService(),
    )

    ServiceRegistry.register(
        RISK,
        ExecutiveRiskService(),
    )

    ServiceRegistry.register(
        OPPORTUNITY,
        ExecutiveOpportunityService(),
    )

    ServiceRegistry.register(
        WORKFLOW,
        WorkflowIntelligenceService(),
    )


def bootstrap_subscribers():

    manager = SubscriptionManager()

    manager.register(
        LoggingSubscriber(),
    )

    manager.register(
        WorkflowAuditSubscriber(),
    )

    manager.register(
        AuditSubscriber(),
    )

    manager.register(
        KnowledgeNotificationSubscriber(),
    )

    return manager