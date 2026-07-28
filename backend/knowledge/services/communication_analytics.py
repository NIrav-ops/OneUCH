"""
Enterprise Communication Analytics Service
"""

from inbox.models import InboxMessage


class CommunicationAnalyticsService:
    """
    Enterprise communication analytics.

    Future metrics:

    - Channel distribution
    - Response SLA
    - AI usage
    - Meeting analytics
    - Executive communication
    """

    def build(
        self,
        *,
        organization,
    ):

        queryset = InboxMessage.objects.filter(
            organization=organization,
        )

        return {

            "total_messages": queryset.count(),

            "gmail": queryset.filter(
                platform="gmail",
            ).count(),

            "outlook": queryset.filter(
                platform="outlook",
            ).count(),

            "teams": queryset.filter(
                platform="teams",
            ).count(),

            "imap": queryset.filter(
                platform="imap",
            ).count(),

        }