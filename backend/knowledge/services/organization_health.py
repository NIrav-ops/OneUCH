"""
Enterprise Organization Health Service
"""

from context.models import BusinessObject

from context.services.customer360 import (
    Customer360Service,
)


class OrganizationHealthService:
    """
    Calculates organization-wide health.
    """

    def build(
        self,
        *,
        organization,
    ):

        customer360 = Customer360Service()

        healthy = 0
        moderate = 0
        risk = 0

        for obj in BusinessObject.objects.filter(
            organization=organization,
        ):

            result = customer360.build(
                business_object=obj,
            )

            status = result["health"]["status"]

            if status == "Healthy":
                healthy += 1

            elif status == "Moderate":
                moderate += 1

            else:
                risk += 1

        total = healthy + moderate + risk

        return {
            "healthy": healthy,
            "moderate": moderate,
            "risk": risk,
            "total": total,
        }