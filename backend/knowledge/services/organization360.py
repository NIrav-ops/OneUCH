"""
Enterprise Organization360 Service

Aggregates every organization-wide intelligence service.
"""

from knowledge.services.organization_metrics import (
    OrganizationMetricsService,
)

from knowledge.services.organization_activity import (
    OrganizationActivityService,
)

from knowledge.services.organization_health import (
    OrganizationHealthService,
)


class Organization360Service:

    def __init__(self):

        self.metrics = (
            OrganizationMetricsService()
        )

        self.activity = (
            OrganizationActivityService()
        )

        self.health = (
            OrganizationHealthService()
        )

    def build(
        self,
        *,
        organization,
    ):

        metrics = self.metrics.build(
            organization=organization,
        )

        activity = self.activity.build(
            organization=organization,
        )

        health = self.health.build(
            organization=organization,
        )

        return {

            "organization": {
                "id": organization.id,
                "name": organization.name,
            },

            "metrics": metrics,

            "activity": activity,

            "health": health,

        }