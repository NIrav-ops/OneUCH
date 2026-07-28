"""
Enterprise Communication Trends Service
"""

from django.db.models import Count
from django.db.models.functions import TruncDate

from inbox.models import InboxMessage


class CommunicationTrendService:
    """
    Daily communication trends.
    """

    def build(
        self,
        *,
        organization,
    ):

        queryset = (

            InboxMessage.objects.filter(
                organization=organization,
            )

            .annotate(
                day=TruncDate("received_at"),
            )

            .values("day")

            .annotate(
                messages=Count("id"),
            )

            .order_by("day")

        )

        trends = []

        for item in queryset:

            trends.append(
                {
                    "day": item["day"],
                    "messages": item["messages"],
                }
            )

        return {

            "days": trends,

            "total_days": len(trends),

        }