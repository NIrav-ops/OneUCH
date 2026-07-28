"""
Enterprise Communication Intelligence Service
"""

from knowledge.services.communication_analytics import (
    CommunicationAnalyticsService,
)

from knowledge.services.channel_analytics import (
    ChannelAnalyticsService,
)

from knowledge.services.communication_trends import (
    CommunicationTrendService,
)

from knowledge.services.response_time_analytics import (
    ResponseTimeAnalyticsService,
)

from knowledge.services.communication_health import (
    CommunicationHealthService,
)


class CommunicationIntelligenceService:
    """
    Enterprise Communication Intelligence.

    Aggregates every communication metric
    into a single intelligence object.
    """

    def __init__(self):

        self.analytics = (
            CommunicationAnalyticsService()
        )

        self.channels = (
            ChannelAnalyticsService()
        )

        self.trends = (
            CommunicationTrendService()
        )

        self.responses = (
            ResponseTimeAnalyticsService()
        )

        self.health = (
            CommunicationHealthService()
        )

    def build(
        self,
        *,
        organization,
    ):

        analytics = self.analytics.build(
            organization=organization,
        )

        channels = self.channels.build(
            organization=organization,
        )

        trends = self.trends.build(
            organization=organization,
        )

        responses = self.responses.build(
            organization=organization,
        )

        health = self.health.build(
            analytics=analytics,
            channels=channels,
            trends=trends,
            response_times=responses,
        )

        return {

            "analytics": analytics,

            "channels": channels,

            "trends": trends,

            "response_times": responses,

            "health": health,

        }