"""
Enterprise Channel Analytics Service
"""

from inbox.models import InboxMessage


class ChannelAnalyticsService:
    """
    Calculates communication statistics grouped by channel.
    """

    CHANNELS = [
        "gmail",
        "outlook",
        "teams",
        "imap",
    ]

    def build(
        self,
        *,
        organization,
    ):

        queryset = InboxMessage.objects.filter(
            organization=organization,
        )

        total = queryset.count()

        channels = []

        for channel in self.CHANNELS:

            count = queryset.filter(
                platform=channel,
            ).count()

            percentage = 0

            if total:

                percentage = round(
                    (count / total) * 100,
                    2,
                )

            channels.append(
                {
                    "channel": channel,
                    "count": count,
                    "percentage": percentage,
                }
            )

        return {
            "total_messages": total,
            "channels": channels,
        }