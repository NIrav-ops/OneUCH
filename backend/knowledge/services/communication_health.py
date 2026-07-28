"""
Enterprise Communication Health Service
"""


class CommunicationHealthService:
    """
    Calculates overall communication health.
    """

    def build(
        self,
        *,
        analytics,
        channels,
        trends,
        response_times,
    ):

        score = 0

        reasons = []

        # Communication volume
        if analytics["total_messages"] > 0:

            score += 25

            reasons.append(
                "Communication activity available"
            )

        # Multiple communication channels
        active_channels = sum(

            1

            for channel in channels["channels"]

            if channel["count"] > 0

        )

        if active_channels > 0:

            score += 25

            reasons.append(
                "Communication channels active"
            )

        # Trend history

        if trends["total_days"] > 0:

            score += 25

            reasons.append(
                "Communication trends available"
            )

        # Response analytics

        if response_times["pairs"] > 0:

            score += 25

            reasons.append(
                "Response analytics available"
            )

        score = min(score, 100)

        if score >= 80:

            status = "Healthy"

        elif score >= 50:

            status = "Moderate"

        else:

            status = "At Risk"

        return {

            "score": score,

            "status": status,

            "reasons": reasons,

        }