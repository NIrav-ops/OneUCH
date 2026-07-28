"""
Enterprise Response Time Analytics Service
"""

from datetime import timedelta

from inbox.models import InboxMessage


class ResponseTimeAnalyticsService:
    """
    Calculates enterprise response metrics.

    Phase 1:
        Average response delay based on message timestamps.

    Future:
        SLA
        Department analytics
        AI predictions
    """

    def build(
        self,
        *,
        organization,
    ):

        queryset = InboxMessage.objects.filter(
            organization=organization,
        ).order_by(
            "received_at",
        )

        messages = list(queryset)

        if len(messages) < 2:

            return {
                "pairs": 0,
                "average_minutes": 0,
                "max_minutes": 0,
                "min_minutes": 0,
            }

        response_minutes = []

        for previous, current in zip(
            messages,
            messages[1:],
        ):

            delta = (
                current.received_at -
                previous.received_at
            )

            response_minutes.append(
                delta.total_seconds() / 60
            )

        return {

            "pairs": len(response_minutes),

            "average_minutes": round(
                sum(response_minutes)
                / len(response_minutes),
                2,
            ),

            "max_minutes": round(
                max(response_minutes),
                2,
            ),

            "min_minutes": round(
                min(response_minutes),
                2,
            ),

        }