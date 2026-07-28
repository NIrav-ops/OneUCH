"""
Enterprise Customer 360 Service

Builds a complete 360° profile for a BusinessObject.

Future:

- AI Summary
- Sentiment
- Risk
- Opportunity
- Timeline
- Communication Analytics
"""

from context.services.graph_repository import GraphRepository
from context.services.graph_traversal import GraphTraversalService
from context.services.relationship_repository import RelationshipRepository
from context.services.relationship_summary import (
    RelationshipSummaryService,
)

from knowledge.services.repository import KnowledgeRepository
from knowledge.services.timeline import (
    TimelineService,
)
from knowledge.services.communication_metrics import (
    CommunicationMetricsService,
)
from knowledge.services.knowledge_summary import (
    KnowledgeSummaryService,
)
from knowledge.services.executive_summary import (
    ExecutiveSummaryService,
)
from knowledge.services.activity_feed import (
    ActivityFeedService,
)
from knowledge.services.health_score import (
    HealthScoreService,
)


class Customer360Service:
    """
    Enterprise Customer 360 Orchestrator.
    """

    def __init__(self):

        self.graph = GraphRepository()

        self.traversal = GraphTraversalService()

        self.relationships = RelationshipRepository()

        self.knowledge = KnowledgeRepository()

        self.timeline = TimelineService()

        self.metrics = CommunicationMetricsService()

        self.knowledge_summary = (
            KnowledgeSummaryService()
        )

        self.relationship_summary = (
            RelationshipSummaryService()
        )

        self.executive_summary = (
            ExecutiveSummaryService()
        )

        self.activity_feed = (
            ActivityFeedService()
        )

        self.health_score = (
            HealthScoreService()
        )        

    def build(
        self,
        *,
        business_object,
    ):
        """
        Build complete Customer360 profile.
        """

        # ----------------------------------------
        # Knowledge
        # ----------------------------------------

        knowledge = self.knowledge_summary.build(
            business_object=business_object,
        )

        # ----------------------------------------
        # Communication Metrics
        # ----------------------------------------

        metrics = self.metrics.build(
            business_object=business_object,
        )

        # ----------------------------------------
        # Relationships
        # ----------------------------------------

        relationships = self.relationship_summary.build(
            business_object=business_object,
        )

        # ----------------------------------------
        # Timeline
        # ----------------------------------------

        timeline = self.timeline.build(
            business_object=business_object,
        )

        # ----------------------------------------
        # Activity
        # ----------------------------------------

        activity = self.activity_feed.build(
            business_object=business_object,
        )

        # ----------------------------------------
        # Executive Summary
        # ----------------------------------------

        summary = self.executive_summary.build(
            business_object=business_object,
            knowledge=knowledge,
            metrics=metrics,
            relationships=relationships,
        )

        # ----------------------------------------
        # Health
        # ----------------------------------------

        health = self.health_score.build(
            knowledge=knowledge,
            metrics=metrics,
            relationships=relationships,
        )

        # ----------------------------------------
        # Customer360 Response
        # ----------------------------------------

        return {
            "business_object": business_object,
            "graph": {},
            "relationships": relationships,
            "knowledge": knowledge,
            "timeline": timeline,
            "metrics": metrics,
            "activity": activity,
            "summary": summary,
            "health": health,
        }